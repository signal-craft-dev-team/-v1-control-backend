from app.mqtt.router import Router
from signalcraft_models.mqtt import edge_cloud_topics as T

from app.handler.file_upload_handler import file_upload_handler
from app.handler.file_upload_result import file_upload_result_handler
from app.handler.param_request import param_request_handler
from app.handler.heartbeat import server_heartbeat_handler, sensor_heartbeat_handler

mqtt_router = Router()
mqtt_router.on(T.e2c("+", T.UPLOAD_REQUEST),   file_upload_handler)
mqtt_router.on(T.e2c("+", T.UPLOAD_RESULT),    file_upload_result_handler)
mqtt_router.on(T.e2c("+", T.PARAM_REQUEST),    param_request_handler)
mqtt_router.on(T.e2c("+", T.SERVER_HEARTBEAT), server_heartbeat_handler)
mqtt_router.on(T.e2c("+", T.SENSOR_HEARTBEAT), sensor_heartbeat_handler)