import ssl
import cv2 as cv
import paho.mqtt.client as mqtt
import base64
import threading
import time
import json
import asyncio
import websockets
import cv2, base64
import random
import string
import requests
from ColorDetector import ColorDetector

def generate_random_number(length):
    for n in range(1,length):
        caracters = string.digits
        random_name = ''.join(random.choice(caracters) for _ in range(length))
    return random_name

def send_video_stream(origin, client):
    global sending_video_stream
    global cap
    topic_to_publish = f"cameraService/{origin}/videoFrame"

    while sending_video_stream:
        # Read Frame
        ret, frame = cap.read()
        if ret:
            _, image_buffer = cv.imencode(".jpg", frame)
            jpg_as_text = base64.b64encode(image_buffer)
            client.publish(topic_to_publish, jpg_as_text)
            time.sleep(0.2)


def send_video_for_calibration(origin, client):
    global sending_video_for_calibration
    global cap
    global colorDetector
    topic_to_publish = f"cameraService/{origin}/videoFrame"

    while sending_video_for_calibration:
        # Read Frame
        ret, frame = cap.read()
        if ret:
            frame = colorDetector.MarkFrameForCalibration(frame)
            _, image_buffer = cv.imencode(".jpg", frame)
            jpg_as_text = base64.b64encode(image_buffer)
            client.publish(topic_to_publish, jpg_as_text)
            time.sleep(0.2)


def send_video_with_colors(origin, client):
    global finding_colors
    global cap
    global colorDetector
    topic_to_publish = f"cameraService/{origin}/videoFrameWithColor"

    while finding_colors:
        # Read Frame
        ret, frame = cap.read()
        if ret:
            frame, color = colorDetector.DetectColor(frame)
            _, image_buffer = cv.imencode(".jpg", frame)
            frame_as_text = base64.b64encode(image_buffer)
            base64_string = frame_as_text.decode("utf-8")
            frame_with_colorJson = {"frame": base64_string, "color": color}
            frame_with_color = json.dumps(frame_with_colorJson)
            client.publish(topic_to_publish, frame_with_color)
            time.sleep(0.2)


# Función asincrónica para transmitir video a través de Websockets
def start_websockets_server(address, port):
    async def transmit(websocket, path):
        print("Client Connected !")
        try:
            # Inicializamos la captura de video desde la cámara (0 indica la cámara predeterminada)
            cap = cv2.VideoCapture(0)

            width = 1280
            height = 960
            fps = 60
            quality = 90

            # Declaramos resolucion de la cámara
            cap.set(3, width)  # 3 -> Ancho de la imagen (Default: 640)
            cap.set(4, height)  # 4 -> Altura de la imagen (Default: 480)
            cap.set(5, fps)  # 5 -> Frames por segundo (min 5fps, intervalos de 5, Default: 30 fps)

            # Consultamos la resolucion de la cámara y los FPS
            print(cap.get(3))
            print(cap.get(4))
            print(cap.get(5))

            # Empezamos un contador
            # st = time.time()

            # while time.time() - st < 1:
            while cap.isOpened():
                # Leemos un fotograma de la cámara
                _, frame = cap.read()

                # Codificamos el fotograma en formato JPG y definimos la calidad de compresión entre 0-100 (Default: 95)
                encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])[1]

                # Convertimos la imagen codificada a base64
                data = str(base64.b64encode(encoded))
                data = data[2:len(data) - 1]

                # Enviamos los datos al cliente a través del socket
                await websocket.send(data)
                print("Tamaño mensaje: ", len(data))

                # Descomenta las líneas siguientes si deseas mostrar la transmisión en el servidor
                # cv2.imshow("Transimission", frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #    break

            # Liberamos la captura de video cuando se cierra la conexión
            cap.release()

        # Manejo de excepciones para manejar desconexiones y otros errores
        except websockets.exceptions.ConnectionClosedError as e:
            print("Error! Client Disconnected !")
            cap.release()
        except websockets.exceptions.ConnectionClosed as e:
            print("Client Disconnected !")
            cap.release()
        except:
            print("Someting went Wrong !")


    # Iniciamos el servidor de Websockets en la dirección IP y el puerto especificados
    start_server = websockets.serve(transmit, host=address, port=port)
    start_server
    # Ejecutamos el bucle de eventos de asyncio para mantener el servidor en ejecución
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

def process_message(message, client):

    global sending_video_stream
    global sending_video_for_calibration
    global finding_colors
    global cap
    global colorDetector
    global recording

    splited = message.topic.split("/")
    origin = splited[0]
    command = splited[2]
    recording = False
    print("recibo ", command, "de ", origin)

    if not cap.isOpened():
        cap = cv.VideoCapture(0)

    if command == "takePicture":
        print("Take picture")
        ret = False
        for n in range(1, 20):
            # this loop is required to discard first frames
            ret, frame = cap.read()
        _, image_buffer = cv.imencode(".jpg", frame)
        # Converting into encoded bytes
        jpg_as_text = base64.b64encode(image_buffer)
        client.publish("cameraService/" + origin + "/picture", jpg_as_text)

    if command == "startVideoStream":
        print("start video stream")
        sending_video_stream = True
        w = threading.Thread(
            target=send_video_stream,
            args=(origin, client),
        )
        w.start()

    if command == "stopVideoStream":
        print("stop video stream")
        sending_video_stream = False

    if command == "markFrameForCalibration":
        print("markFrameForCalibration")
        sending_video_for_calibration = True
        w = threading.Thread(
            target=send_video_for_calibration,
            args=(origin, client),
        )
        w.start()
    if command == "stopCalibration":
        print("stop calibration")
        sending_video_for_calibration = False
    if command == "getDefaultColorValues":
        yellow, green, blueS, blueL, pink, purple = colorDetector.DameValores()
        colorsJson = {
            "yellow": yellow,
            "green": green,
            "blueS": blueS,
            "blueL": blueL,
            "pink": pink,
            "purple": purple,
        }
        colors = json.dumps(colorsJson)
        print("envio: ", colorsJson)
        client.publish("cameraService/" + origin + "/colorValues", colors)
    if command == "getColorValues":
        colorDetector.TomaValores()
        print("ya he tomado los valroe")
        yellow, green, blueS, blueL, pink, purple = colorDetector.DameValores()
        colorsJson = {
            "yellow": yellow,
            "green": green,
            "blueS": blueS,
            "blueL": blueL,
            "pink": pink,
            "purple": purple,
        }
        print("voy a enviar: ", colorsJson)
        colors = json.dumps(colorsJson)
        print("envio: ", colorsJson)
        client.publish("cameraService/" + origin + "/colorValues", colors)

    if command == "takeValues":
        colorDetector.TomaValores()

    if command == "startFindingColor":
        finding_colors = True
        w = threading.Thread(
            target=send_video_with_colors,
            args=(origin, client),
        )
        w.start()
    if command == "stopFindingColor":
        finding_colors = False
    if command == "dronestream_websockets":
        print("Starting live camera")
        start_websockets_server("192.168.1.63", 42888)
    if command == "get_all_flightPlans":
        print("FLIGHT PLANS:\n", message.payload)

    if command == "takePictureFlightPlan":
        print("Take picture for Flight Plan")
        ret = False
        for n in range(1, 20):
            # this loop is required to discard first frames
            ret, frame = cap.read()
        _, image_buffer = cv.imencode('.jpg', frame)
        if ret:
            random_number = generate_random_number(3)
            random_name = "picture_" + random_number + ".jpg"
            route = 'Pictures/' + random_name
            # Guardar imagen provisionalmente
            cv.imwrite(route, frame)
            internal_client.publish(origin + "/autopilotService/savePicture", random_name)

    if command == "takePictureInterval":
        print("Take picture by interval")
        ret = False
        for n in range(1, 20):
            # this loop is required to discard first frames
            ret, frame = cap.read()
        _, image_buffer = cv.imencode('.jpg', frame)
        #jpg_as_text = base64.b64encode(image_buffer)
        if ret:
            random_number = generate_random_number(3)
            random_name = "pictureInterval_" + random_number + ".jpg"
            route = 'Pictures/' + random_name
            cv.imwrite(route, frame)
            internal_client.publish(origin + "/autopilotService/savePictureInterval", random_name)


    if command == "startVideoMoving":
        def start_recording():
            fourcc = cv.VideoWriter_fourcc(*"mp4v")
            random_number = generate_random_number(3)
            random_name = "videoMoving_" + random_number + ".mp4"
            route = 'Videos/' + random_name
            output_video = cv.VideoWriter(route, fourcc, 30.0, (640, 480))
            print("Filmando video " + random_name)
            while recording == True:
                ret, frame = cap.read()
                output_video.write(frame)
            cv.destroyAllWindows()
            output_video.release()
            print ("Video grabado")
            internal_client.publish(origin + "/autopilotService/saveVideo", random_name)
        if recording == False:
            recording = True
            recording_thread = threading.Thread(target=start_recording)
            recording_thread.start()

    if command == "endVideoMoving":
        recording = False
        print ("Video se tiene que parar")

    if command == "startStaticVideo":
        durationVideo = int(message.payload.decode("utf-8"))
        def start_recording_static_video(duration):
            fourcc = cv.VideoWriter_fourcc(*"mp4v")
            random_number = generate_random_number(3)
            random_name = "staticVideo_" + random_number + ".mp4"
            print ("Filmando video " + random_name)
            route = 'Videos/' + random_name
            output_video = cv.VideoWriter(route, fourcc, 30.0, (640, 480))
            start_time = time.time()
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                output_video.write(frame)
            output_video.release()
            print("Video estático grabado")
            internal_client.publish(origin + "/autopilotService/saveVideo", random_name)
            # shutil.move(random_name, "/Videos/" + random_name)
        recording_thread = threading.Thread(target=start_recording_static_video(durationVideo))
        recording_thread.start()

    if command == "saveMediaApi":
        flight_id = message.payload.decode("utf-8")
        response_json = requests.get('http://localhost:9000/get_results_flight/' + flight_id).json()
        pictures = response_json["Pictures"]
        for picture in pictures[0:]:
            picture_name = picture["namePicture"]
            image_path = 'Pictures/' + picture_name
            print(f"Buscando picture: {image_path}")
            with open(image_path, 'rb') as file:
                image_buffer = file.read()
            requests.post(f"http://localhost:8105/save_picture/{picture_name}", image_buffer)
        videos = response_json["Videos"]
        for video in videos[0:]:
            video_name = video["nameVideo"]
            video_path = 'Videos/' + video_name
            print(f"Buscando video: {video_path}")
            with open(video_path, 'rb') as file:
                video_buffer = file.read()
            requests.post(f"http://localhost:8105/save_video/{video_name}", video_buffer)



def on_internal_message(client, userdata, message):
    print("recibo internal ", message.topic)
    global internal_client
    process_message(message, internal_client)


def on_external_message(client, userdata, message):
    print("recibo external ", message.topic)

    global external_client
    process_message(message, external_client)


def on_connect(external_client, userdata, flags, rc):
    if rc == 0:
        print("Connection OK")
    else:
        print("Bad connection")


def CameraService(connection_mode, operation_mode, external_broker, username, password):
    global op_mode
    global external_client
    global internal_client
    global state
    global cap
    global colorDetector

    sending_video_stream = False

    cap = cv.VideoCapture(0)  # video capture source camera (Here webcam of lap>

    colorDetector = ColorDetector()

    print("Camera ready")

    print("Connection mode: ", connection_mode)
    print("Operation mode: ", operation_mode)
    op_mode = operation_mode

    internal_client = mqtt.Client("Autopilot_internal")
    internal_client.on_message = on_internal_message
    internal_client.connect("localhost", 1884)

    state = "disconnected"

    print("Connection mode: ", connection_mode)
    print("Operation mode: ", operation_mode)
    op_mode = operation_mode

    internal_client = mqtt.Client("Camera_internal")
    internal_client.on_message = on_internal_message
    internal_client.connect("localhost", 1884)

    external_client = mqtt.Client("Camera_external", transport="websockets")
    external_client.on_message = on_external_message
    external_client.on_connect = on_connect

    if connection_mode == "global":
        if external_broker == "hivemq":
            external_client.connect("broker.hivemq.com", 8000)
            print("Connected to broker.hivemq.com:8000")

        elif external_broker == "hivemq_cert":
            external_client.tls_set(
                ca_certs=None,
                certfile=None,
                keyfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None,
            )
            external_client.connect("broker.hivemq.com", 8884)
            print("Connected to broker.hivemq.com:8884")

        elif external_broker == "classpip_cred":
            external_client.username_pw_set(username, password)
            external_client.connect("classpip.upc.edu", 8000)
            print("Connected to classpip.upc.edu:8000")

        elif external_broker == "classpip_cert":
            external_client.username_pw_set(username, password)
            external_client.tls_set(
                ca_certs=None,
                certfile=None,
                keyfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None,
            )
            external_client.connect("classpip.upc.edu", 8883)
            print("Connected to classpip.upc.edu:8883")
        elif external_broker == "localhost":
            external_client.connect("localhost", 8000)
            print("Connected to localhost:8000")
        elif external_broker == "localhost_cert":
            print("Not implemented yet")

    elif connection_mode == "local":
        if operation_mode == "simulation":
            external_client.connect("localhost", 8000)
            print("Connected to localhost:8000")
        else:
            external_client.connect("10.10.10.1", 8000)
            print("Connected to 10.10.10.1:8000")

    print("Waiting....")
    external_client.subscribe("+/cameraService/#", 2)
    internal_client.subscribe("+/cameraService/#")
    internal_client.loop_start()
    external_client.loop_forever()


if __name__ == "__main__":
    import sys

    connection_mode = sys.argv[1]  # global or local
    operation_mode = sys.argv[2]  # simulation or production
    username = None
    password = None
    if connection_mode == "global":
        external_broker = sys.argv[3]
        if external_broker == "classpip_cred" or external_broker == "classpip_cert":
            username = sys.argv[4]
            password = sys.argv[5]
    else:
        external_broker = None

    CameraService(connection_mode, operation_mode, external_broker, username, password)


