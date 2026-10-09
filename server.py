import socket
import threading
import protocol as proto

HOST = "0.0.0.0"
PORT = 5555

tasks = []

tasks_lock = threading.Lock()


def parse_number(arg):
    try:
        return int(arg.strip())
    except ValueError:
        return None


def cmd_add(arg):
    if not arg:
        return
    with tasks_lock:
        tasks.append({"text": arg, "done": False})
        number = len(tasks)
    return "TEXT", f"* задача №{number} добавлена"


def cmd_list(arg):
    with tasks_lock:
        lines = [
            f"{i}. [{'x' if t['done'] else ' '}] {t['text']}"
            for i, t in enumerate(tasks, start=1)
        ]
    if not lines:
        return "TEXT", "Список задач пуст"
    return "LIST", "\n".join(lines)


def cmd_done(arg):
    number = parse_number(arg)
    if number is None:
        return "ERROR", "некорректный /done: нужен номер задачи. Пример: /done 2"
    with tasks_lock:
        if not 1 <= number <= len(tasks):
            return "ERROR", f"задачи с номером {number} не существует"
        tasks[number - 1]["done"] = True
        text = tasks[number - 1]["text"]
    return "TEXT", f"* задача №{number} выполнена: {text}"


HANDLERS = {
    "ADD": cmd_add,
    "LIST": cmd_list,
    "DONE": cmd_done,
}


def handle_client(sock, addr):
    print(f"[+] подключился {addr}")
    try:
        while True:
            msg = proto.recv_message(sock)
            if msg is None:
                print(f"[i] {addr} отключился без QUIT")
                break

            command, payload = msg
            arg = payload.decode("utf-8", errors="replace").strip()

            if command == "QUIT":
                proto.send_message(sock, "TEXT", b"* bye")
                print(f"[-] {addr} вышел через QUIT")
                break

            handler = HANDLERS.get(command)
            if handler is None:
                # Некорректная команда: отвечаем ошибкой, но не падаем
                reply = ("ERROR", f"неизвестная команда {command}")
            else:
                reply = handler(arg)

            reply_command, reply_text = reply
            proto.send_message(sock, reply_command, reply_text.encode("utf-8"))

    except ConnectionResetError:
        print(f"[!] {addr} - соединение сброшено (RST)")
    except BrokenPipeError:
        print(f"[!] {addr} - не удалось отправить, соединение разорвано")
    except ValueError as e:
        print(f"[!] {addr} - нарушение протокола: {e}")
        try:
            proto.send_message(sock, "ERROR", f"protocol error: {e}".encode("utf-8"))
        except OSError:
            pass
    except ConnectionError:
        print(f"[!] {addr} - соединение оборвано посреди сообщения")
    finally:
        sock.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"[*] сервер слушает {HOST}:{PORT}")
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] сервер остановлен")
