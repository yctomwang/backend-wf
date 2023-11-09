import flask
import json
import docker
from app import db, app
import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
import requests
import time


def fetch_database_postgres_eo(database_name: str, username: str, pwd: str, hostname: str, port_num: str,
                               table_name: str):
    """
        Connects to a PostgreSQL database and retrieves all rows from a specified table.

        Args:
            database_name (str): The name of the PostgreSQL database.
            username (str): The username to authenticate with the database.
            pwd (str): The password to authenticate with the database.
            hostname (str): The hostname or IP address of the database server.
            port_num (str): The port number to connect to the database.
            table_name (str): The name of the table to fetch data from.

        Returns:
            list: A list of tuples representing the fetched rows from the table.
        """
    conn = psycopg2.connect(database=database_name, user=username, password=pwd, host=hostname,
                            port=port_num)

    cur = conn.cursor()
    query = "SELECT * FROM {};".format(table_name)
    cur.execute(query, (table_name,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@pytest.fixture(scope="module")
def postgres_container():
    postgres = PostgresContainer(dbname="test_pam", user="test_pam", password="test_pam")
    postgres.with_bind_ports(5432, 5432)  # port binding local with docker img
    postgres.start()
    yield postgres
    postgres.stop()


# New fixture that gets parameters directly from the test function
@pytest.fixture(scope="function")
def eo_params(request):
    """
    this fixture is a walk-around for not been able to directly pass from test into fixtures thats not directly called
    """
    return request.param


#
def wait_for_downstream_containers(timeout=30):
    """will check to see if downstream engineering order and postgres container along with container for pam task
    is running or not. maximum timeout is 30 seconds
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # check if connection can be made with eo db
            connection_eo_db = psycopg2.connect(
                dbname="test_pam",
                user="test_pam",
                password="test_pam",
                host="127.0.0.1",
                port="5433"
            )
            connection_eo_db.close()
            # check if connection can be made with pam task db
            connection_pam_db = psycopg2.connect(
                dbname="test_pam",
                user="test_pam",
                password="test_pam",
                host="127.0.0.1",
                port="5432"
            )
            connection_pam_db.close()
            # check if healthcheck for eo is returning 200 code
            response = requests.get("http://127.0.0.1:5079/api/v1/engineering-orders/healthcheck")
            if response.status_code != 200:
                raise Exception  # Downstream container is available as of yet
            return True
        except Exception:
            # pass  # Connection error, continue waiting
            time.sleep(1)  # Wait for 1 second before retrying
    return False  # Timeout reached, downstream container is not available


def pull_if_not_exist(client, image_name):
    """a little util function written...."""
    images = [img for img in client.images.list() if image_name in img.tags]
    if not images:
        return client.images.pull(image_name)
    return images[0]


@pytest.fixture(scope="function")
def setup_docker_network():
    client = docker.from_env()

    # create a network (or get it if it already exists)
    network_name = 'TEST_EO_PAM'

    # try to get the network and destroy it if it exists
    try:
        network = client.networks.get(network_name)
        network.remove()
    except docker.errors.NotFound:
        pass

    # create a new network
    network = client.networks.create(network_name, driver="bridge")

    # yield the network, client, and network_name for use in the test
    yield {'network': network, 'client': client, 'network_name': network_name}

    # after the test function has finished, remove the network
    network.remove()


@pytest.fixture(scope="function")
def setup_rabbit_mq(setup_docker_network):
    client = setup_docker_network['client']
    network_name = setup_docker_network['network_name']
    network = setup_docker_network['network']
    pull_if_not_exist(client, 'rabbitmq:latest')


@pytest.fixture(scope="function")
def setup_eo_postgres(setup_docker_network):
    client = setup_docker_network['client']
    network_name = setup_docker_network['network_name']
    network = setup_docker_network['network']

    pull_if_not_exist(client, 'postgres:latest')

    # run a container using the pulled image
    container = client.containers.run('postgres:latest',
                                      detach=True,
                                      environment={

                                          "POSTGRES_USER": "test_pam",
                                          "POSTGRES_PASSWORD": "test_pam",
                                          "POSTGRES_DB": "test_pam"
                                      },
                                      ports={'5432/tcp': 5432},
                                      name="easteregg_weloveThomas",
                                      auto_remove=True,
                                      network=network_name)
    time.sleep(5)
    yield {'network': network, 'client': client, 'network_name': network_name, 'eo_postgres': container}
    container.stop()


@pytest.fixture(scope="function")
def set_up_eo_ms(setup_eo_postgres):
    client = setup_eo_postgres['client']
    network_name = setup_eo_postgres['network_name']
    network = setup_eo_postgres['network']
    eo_container = setup_eo_postgres['eo_postgres']
    # time.sleep(10)
    # pull_if_not_exist(client, "harbor.dna.networks.au.singtelgroup.net/ipne-automation/ngce-automation/engineering-orders@sha256:8ec1ecdc219ca395373b28478dd23410f14b1393f04dd3d1710b174686a36a5d")

    # run a container using the pulled image
    attrs = eo_container.attrs

    # Extract the IP address from the network settings
    ip_address = attrs['NetworkSettings']['Networks']['TEST_EO_PAM']['IPAddress']
    container = client.containers.run(
        "harbor.dna.networks.au.singtelgroup.net/ipne-automation/ngce-automation/engineering-orders@sha256:e82cb15fcdbe19ea604fee80920a6d51abb34227d3bd5d4fc333e3a4f7061c76",
        detach=True,
        environment={
            "SQLALCHEMY_DATABASE_URI": "postgresql://test_pam:test_pam@" + "easteregg_weloveThomas" + ":5432/test_pam"},
        ports={'8000': 5079},
        network=network_name,
        auto_remove=True
        )

    yield {'network': network, 'client': client, 'network_name': network_name, 'eo_postgres': eo_container,
           'eo_ms': container}
    container.stop()


@pytest.fixture(scope="function")
def populate_eo_db(eo_params, set_up_eo_ms):
    eo_ms_container_name = set_up_eo_ms['eo_ms']

    # check to see if down stream containers are alive
    if not wait_for_downstream_containers():
        assert False, "Downstream containers did not become available within the timeout"
    # time.sleep(10)
    number_of_eo_entry = eo_params.get("number_of_eo_entry")
    eo_number_list = eo_params.get("eo_number_list")
    eo_status_list = eo_params.get("eo_status_list")
    # connect to eo_postgres db

    conn = psycopg2.connect(
        dbname="test_pam",
        user="test_pam",
        password="test_pam",
        host="127.0.0.1",
        port="5433"
    )

    # Open a cursor to perform database operations
    cur = conn.cursor()
    payload = {
        "ngce-device-manager:device-manager": "thomas is the greatest he is the best ;)"
    }

    for i in range(number_of_eo_entry):
        eo_number = eo_number_list[i]
        status = eo_status_list[i]
        # prepare the sql statement
        sql = """
            INSERT INTO public.eos (eo_number, status, eo_type, payload, created, updated)
            VALUES (%s, %s, 'Tx Equipment', %s, '2023-05-17 10:30:00', '2023-05-17 10:45:00');
            """
        # execute the sql statement
        cur.execute(sql, (eo_number, status, json.dumps(payload)))

    conn.commit()
    cur.close()
    conn.close()


@pytest.mark.integration
@pytest.mark.parametrize('valid_payload, eo_params', [
    (
            {'task_name': 'T2b_NSO_Run_Pre-check', 'task_status': 'Completed'},
            {'number_of_eo_entry': 1, 'eo_number_list': [456], 'eo_status_list': ["Ready"]}
    )
], indirect=True)
def test_integeration_eo1(mocked_db_app: flask.Flask, valid_payload, postgres_container, populate_eo_db, eo_params):
    """test_integeration_eo1: Verifies the PAM task's behavior for the '
    T2b_NSO_Run_Pre-check' with task status 'Completed'."""
    with app.app_context():
        # ensure schemas are created
        db.create_all()

    test_client = mocked_db_app.test_client()
    # if not wait_for_downstream_containers():
    #     assert False, "Downstream containers did not become available within the timeout"

    # populate_eo_db({'number_of_eo_entry': 1, 'eo_number_list': [456], 'eo_status_list': ["Ready"]})
    response = test_client.post('/api/v1/pam/tasks', json=valid_payload, content_type='application/json')
    # check status code is all good
    assert response.status_code == 201
    fetched_eo_postgres = fetch_database_postgres_eo(database_name="test_pam", username="test_pam", pwd="test_pam",
                                                     hostname="localhost",
                                                     port_num="5433", table_name="eos")
    # print(fetched_eo_postgres)
    assert fetched_eo_postgres[0][2] == 'In Progress'
    # print(type(fetched_eo_postgres))
