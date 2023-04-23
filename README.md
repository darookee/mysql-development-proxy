# MySQL proxy with query logging

This is a simple MySQL proxy with query logging implemented using Flask and python's `socket` library.

## How it works
This proxy listens on port 3306 and proxies all traffic to a MySQL server running on a specified host and port (defaults to `db` and `3306` respectively).

All incoming queries are parsed and stored in memory. They can be retrieved by sending a GET request to the root URL (`/`).

Queries can be cleared by sending a GET request to `/reset`.

## Installation
1. Clone the repository.
2. Install the requirements using `pip install -r requirements.txt`.
3. Run the server using `python server.py`.

By default, the proxy connects to a MySQL server running on `db:3306`. You can specify a different host and port by setting the `TARGET_HOST` and `TARGET_PORT` environment variables.

## Usage
Once the proxy is running, you can connect to it using any MySQL client, just like you would with a regular MySQL server. The queries you execute will be logged and stored in memory.

To retrieve the list of queries, send a GET request to the root URL (`/`). The response will be a plain text list of queries.

To clear the list of queries, send a GET request to `/reset`.

## Notes
- This proxy is not intended for use in production environments.
- Binary data in queries is not converted, which may result in problems when using the stored queries.
- If you want to disable encrypted MySQL connections, set the `FORCE_UNENCRYPTED` environment variable to `1`.
