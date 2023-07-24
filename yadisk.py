#!/usr/bin/python3

"""
Скрипт загрузки файла на яндекс.диск

Использовать: <script_name> -s <Путь к файлу> --d <в какую папку на диске положить>
параметр --d не обязателен.
!!! Добавьте токен авторизации в переменную окружения YANDEX_AUTH_TOKEN перед использованием.
Для работы через http/https прокси добавьте переменную окружения YA_HTTP_PROXY и укажите в ней адрес прокси с протоколом

!!! Папки на Яндекс.Диске нужно создавать вручную.
!!! Скрипт заливает только 1 файл за вызов.
"""

import os
import sys
from pathlib import Path, PurePosixPath
from argparse import ArgumentParser
import requests


if not os.environ.get('YANDEX_AUTH_TOKEN', False):
    print("Добавьте токен авторизации в переменную окружения YANDEX_AUTH_TOKEN перед использованием.")
    sys.exit(1)

exit_codes = []


def upload(file: Path, upload_to: PurePosixPath = PurePosixPath(''), overwrite: bool = True, exit_result=exit_codes):
    """
    :param file: Путь к файлу
    :param upload_to: Путь на яндекс диске, корнем является папка "Приложения" !!! "/" на конце обязателен
    :param overwrite: Перезаписывать если файл существует?
    :return:
    """
    print("Размер:", file.stat().st_size / (1024**3), "GB")
    session = requests.Session()
    if os.environ.get("YA_HTTP_PROXY", False):
        session.proxies = {"HTTP": os.environ["YA_HTTP_PROXY"], "HTTPS": os.environ["YA_HTTP_PROXY"]}

    session.headers = {"Authorization": f"OAuth {os.environ['YANDEX_AUTH_TOKEN']}"}
    upload_url_request = "https://cloud-api.yandex.net:443/v1/disk/resources/upload/?"\
                 f"path=app:/{upload_to/file.name}&overwrite={str(overwrite).lower()}"

    upload_url = session.get(upload_url_request).json()
    assert upload_url.get("href", False), f"Ну удалось получить url для загрузки файла. Ответ Api: {upload_url}"

    try:
        print("Uploading...")
        with open(file, 'rb') as data:
            upload_request = session.put(upload_url["href"], data=data)
        if upload_request.status_code == 201:
            print("Файл успешно загружен.")

        elif upload_request.status_code == 202:
            print("Файл принят сервером, но еще не был перенесен непосредственно в Яндекс.Диск")

        elif upload_request.status_code == 413:
            print("Слишком большой файл, лимит на размер файла равен 50GB.")
            exit_result.append(1)

        elif upload_request.status_code in [500, 503]:
            print("HTTP 500/503, Яше плохо. Попробуйте позже.")
            exit_result.append(1)

        elif upload_request.status_code == 507:
            print("На Яндекс.Диске закончилось место.")
            exit_result.append(1)

    except FileNotFoundError:
        print("Файл", file, "не найден. Проверьте правильность пути.")

    except requests.exceptions.ConnectTimeout:
        print("Недоступен сервер Яндекс.Диск или проблемы с сетью.")


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-s", type=str, help="Локальный путь к загружаемомму файлу")
    arg_parser.add_argument("--d", type=str, default='', help="Папка, в которую следует поместить файл на Яндекс.Диске")
    args = arg_parser.parse_args()
    upload(Path(args.s), upload_to=PurePosixPath(args.d))
    if 1 in exit_codes:
        sys.exit(1)
