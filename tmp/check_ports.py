import socket

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except Exception:
            return False

print("PORT_8000:", check_port(8000))
print("PORT_5173:", check_port(5173))
