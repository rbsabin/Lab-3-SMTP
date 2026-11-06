from socket import *
import ssl
import base64
import certifi
from getpass import getpass

# Original message provided in the lab skeleton
msg = "\r\n I love computer networks!"
endmsg = "\r\n.\r\n"

# Gmail SMTP server
mailserver = "smtp.gmail.com"
mailport = 587

# Get sender and recipient information
sender = input("Enter your Gmail address: ").strip()
recipient = input("Enter recipient email address: ").strip()
app_password = getpass("Enter your Gmail App Password: ").replace(" ", "")


# Receive the complete SMTP response
def receive_response(clientSocket):
    response = b""

    while True:
        char = clientSocket.recv(1)

        if not char:
            raise ConnectionError("Connection closed by SMTP server.")

        response += char

        if response.endswith(b"\r\n"):
            lines = response.split(b"\r\n")
            last_line = lines[-2]

            # Space after the status code indicates the final response line
            if len(last_line) >= 4 and last_line[3:4] == b" ":
                break

    return response.decode("utf-8", errors="replace")


# Verify SMTP response
def check_response(response, expected_codes, step):
    if response[:3] not in expected_codes:
        raise RuntimeError(
            f"{step} failed. Server response: {response.strip()}"
        )


# Send SMTP command and receive response
def send_command(clientSocket, command, expected_codes, step):
    clientSocket.sendall((command + "\r\n").encode("ascii"))
    response = receive_response(clientSocket)

    print(response, end="")
    check_response(response, expected_codes, step)

    return response


clientSocket = None

try:
    # Establish TCP connection with Gmail SMTP server
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((mailserver, mailport))

    recv = receive_response(clientSocket)
    print(recv)
    check_response(recv, ("220",), "Server connection")

    # Send EHLO command (supports SMTP extensions)
    send_command(
        clientSocket, "EHLO Alice", ("250",), "EHLO"
    )

    # Start TLS encryption
    send_command(
        clientSocket, "STARTTLS", ("220",), "STARTTLS"
    )

    # Establish secure TLS connection
    context = ssl.create_default_context(cafile=certifi.where())
    clientSocket = context.wrap_socket(
        clientSocket, server_hostname=mailserver
    )

    print("TLS encryption established.")

    # Send EHLO again after TLS
    send_command(
        clientSocket, "EHLO Alice", ("250",), "EHLO after TLS"
    )

    # Authenticate with Gmail
    send_command(
        clientSocket, "AUTH LOGIN", ("334",), "AUTH LOGIN"
    )

    # Send Base64 encoded Gmail address
    encoded_email = base64.b64encode(
        sender.encode("utf-8")
    ).decode("ascii")

    send_command(
        clientSocket, encoded_email, ("334",), "Username authentication"
    )

    # Send Base64 encoded Gmail App Password
    encoded_password = base64.b64encode(
        app_password.encode("utf-8")
    ).decode("ascii")

    send_command(
        clientSocket, encoded_password, ("235",), "Password authentication"
    )

    # Send MAIL FROM command
    send_command(
        clientSocket,
        f"MAIL FROM:<{sender}>",
        ("250",),
        "MAIL FROM"
    )

    # Send RCPT TO command
    send_command(
        clientSocket,
        f"RCPT TO:<{recipient}>",
        ("250", "251"),
        "RCPT TO"
    )

    # Send DATA command
    send_command(
        clientSocket, "DATA", ("354",), "DATA"
    )

    # Construct email with separate headers and body
    message = (
        f"From: {sender}\r\n"
        f"To: {recipient}\r\n"
        "Subject: SMTP Programming Lab\r\n"
        "\r\n"
        "I love computer networks!"
    )

    # Send email message
    clientSocket.sendall(
        (message + endmsg).encode("utf-8")
    )

    recv_message = receive_response(clientSocket)
    print(recv_message)
    check_response(recv_message, ("250",), "Sending email")

    print("Email submitted successfully to Gmail.")

    # Send QUIT command
    send_command(
        clientSocket, "QUIT", ("221",), "QUIT"
    )

except (OSError, ssl.SSLError, ConnectionError, RuntimeError) as error:
    print(f"SMTP error: {error}")

finally:
    if clientSocket is not None:
        clientSocket.close()
        print("SMTP connection closed.")
