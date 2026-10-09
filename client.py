import socket
import threading
import protocol as proto

HOST = "127.0.0.1"
PORT = 5555


def listen_loop(sock, stop_event):
    while not stop_event.is_set():
        try:
            msg = proto.recv_message(sock)
        except (OSError, ValueError):
            msg = None
        if msg is None:
            if not stop_event.is_set():
                print("\n[!] соединение с сервером потеряно")
                stop_event.set()
            break
        command, payload = msg
        text = payload.decode("utf-8", errors="replace")
        if command == "ERROR":
            print(f"\n[ошибка] {text}\n> ", end="")
        else:
            print(f"\n{text}\n> ", end="")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except OSError as e:
        print(f"Не удалось подключиться: {e}")
        sock.close()
        return

    stop_event = threading.Event()
    listener = threading.Thread(target=listen_loop, args=(sock, stop_event), daemon=True)
    listener.start()

    print("Команды: /add <текст>, /list, /done <номер>, /quit")
    try:
        while not stop_event.is_set():
            line = input("> ").strip()
            if not line:
                continue
            if not line.startswith("/"):
                print("Команда должна начинаться с '/'. Например: /list")
                continue

            name, _, arg = line[1:].partition(" ")
            command = name.upper()

            try:
                proto.send_message(sock, command, arg.strip().encode("utf-8"))
            except ValueError as e:
                print(f"[ошибка] {e}")
                continue

            if command == "QUIT":
                break
    except (EOFError, KeyboardInterrupt, BrokenPipeError, OSError):
        pass
    finally:
        stop_event.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
        listener.join(timeout=2)


if __name__ == "__main__":
    main()
