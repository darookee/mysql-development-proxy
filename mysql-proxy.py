from flask import Flask, Response
import socket
import os
import logging
import threading
import sqlparse
import select
import struct
from threading import Thread

debug = os.environ.get('DEBUG', False)
if debug != '1':
    debug = False

force_unencrypted = os.environ.get('FORCE_UNENCRYPTED', False)
if force_unencrypted != '1':
    force_unencrypted = False

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG if debug else logging.INFO)
logger = logging.getLogger(__name__)

stored_queries = []

app = Flask(__name__)


@app.route('/')
def home():
    query_list = ';\n'.join(stored_queries)

    return Response(query_list, content_type='text/plain')


@app.route('/reset')
def reset():
    global stored_queries
    stored_queries = []

    return Response('', content_type='text/plain')


def handle_client(client_sock, addr):
    target_host = os.environ.get('TARGET_HOST', 'db')
    target_port = int(os.environ.get('TARGET_PORT', 3306))

    logger.info(f"Connecting to {target_host}:{target_port}")
    # Connect to the target server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((target_host, target_port))
    logger.info("Server connection established.")

    while True:
        logger.debug("Starting the loop...")
        r, _, _ = select.select([server_sock], [], [], 0.1)
        if r:
            # Read data from the server
            server_data = server_sock.recv(1024)
            if not server_data:
                break

            logger.debug(f"Received from server: {server_data}")
            # apparently this is the handshake
            if force_unencrypted and server_data[0] > 4 and server_data[4] == 10:
                # disable SSL capabilities
                logger.info('Disabling SSL in server handshake')
                ssl_capability_flags = struct.unpack('<H', server_data[32:34])[0]
                ssl_capability_flags &= ~2
                server_data = server_data[:32] + struct.pack('<H', ssl_capability_flags) + server_data[34:]

            # Send the data to the client
            client_sock.sendall(server_data)
            logger.debug(f"Sent data to client: {server_data}")

        r, _, _ = select.select([client_sock], [], [], 0.1)
        if r:
            # Read data from the client
            client_data = client_sock.recv(1024)
            if not client_data:
                break
            logger.debug(f"Received from client: {client_data}")

            # if this is a handshake modify it to disable ssl
            if force_unencrypted and client_data[0] > 4 and client_data[4] == 1:
                logger.info('Disabling SSL in client handshake')
                client_data = bytearray(client_data)
                client_data[4] &= ~2
                client_data = bytes(client_data)

            # Send the data to the server
            server_sock.sendall(client_data)
            logger.debug(f"Sent data to server: '{client_data}")

            # test if it is a query packet
            if client_data[0] > 4 and client_data[4] == 3:
                packet_len = int.from_bytes(client_data[0:3], byteorder='little')
                logger.debug(f"Packet length: {packet_len}")

                if packet_len < 1:
                    break

                while len(client_data) < packet_len+4:
                    # receiving more data
                    more_data = client_sock.recv(1024)
                    logger.debug(f"receiving more data... {more_data}")
                    if not more_data:
                        break
                    # and passing it to the server
                    server_sock.sendall(more_data)
                    logger.debug(f"Sent data to server: '{more_data}")
                    client_data += more_data

                logger.debug(f"Final client data: '{client_data}")

                # now the mysql packet should be complete, we should have the whole statement
                query = client_data[5:packet_len+4]
                logger.info(f"Received query '{query}'")

                if not query:
                    break

                try:
                    parsed = sqlparse.parse(query)[0]
                    logger.info(f"Detected query type: '{parsed.get_type()}'")
                    logger.debug(f"Parsed tokens: {parsed.tokens}")
                    # TODO: check for type + log
                    if not (parsed.get_type() == 'SELECT' or parsed.get_type() == 'UNKNOWN'):
                        logger.info(f"Storing '{query}'")
                        # TODO: binary data in queries is not converted which may result in problems when using the stored queries
                        stored_queries.append(query.decode('utf-8', 'replace'))
                except sqlparse.exceptions.SQLParseError:
                    # this should probably not concern us, but it's interesting to know
                    logger.error(f"Invalid query: {query}")

                # reset buffer?
                client_data = b''

    # Close the client and server sockets
    client_sock.close()
    server_sock.close()


def start_server():
    # Create a TCP/IP socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allow reusing the address if the server is restarted quickly
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to a specific address and port
    server_address = ('', 3306)
    server_sock.bind(server_address)

    # Listen for incoming connections
    server_sock.listen(1)
    logger.info(f"Starting Proxy at {server_address}...")

    while True:
        # Wait for a client connection
        client_sock, addr = server_sock.accept()
        logger.info(f'New client connection from {addr}')

        # Handle the client connection in a new thread
        client_thread = threading.Thread(target=handle_client, args=(client_sock, addr))
        client_thread.start()


def start_http():
    app.run(host='0.0.0.0', port=8080)


if __name__ == '__main__':
    proxy_thread = Thread(target=start_server)
    proxy_thread.start()

    flask_thread = Thread(target=start_http)
    flask_thread.start()

    proxy_thread.join()
    flask_thread.join()
