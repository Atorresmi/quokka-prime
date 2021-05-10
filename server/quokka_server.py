from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api, Resource
from quokka_server_utils import get_hostname_from_target, get_ip_address_from_target

from apidoc_models import ApiModels

quokka_app = Flask(__name__)
CORS(quokka_app)

api = Api(quokka_app, version="1.0", title="Quokka", description="Quokka for 52-weeks-of-python",
          default="quokka", default_label="")
ApiModels.set_api_models(api)

from db_apis import get_all_hosts, set_host
from db_apis import get_all_devices, set_device
from db_apis import get_all_services, set_service
from db_apis import get_capture, get_portscan, get_traceroute

from db_apis import record_portscan_data, record_traceroute_data, record_capture_data
from worker_apis import start_portscan, start_traceroute, start_capture


@api.route("/hosts")
class HostsEndpoint(Resource):

    @staticmethod
    @api.response(200, 'Success', ApiModels.hosts_response)
    def get():
        return get_all_hosts()

    @staticmethod
    @api.doc(params={"hostname": "Hostname of host to add or update"}, body=ApiModels.host_fields)
    @api.response(204, 'Success')
    @api.response(400, 'Must provide hostname to add/update host')
    def put():
        hostname = request.args.get("hostname")
        if not hostname:
            return "Must provide hostname to add/update host", 400

        host = request.get_json()
        set_host(host)
        return {}, 204


@api.route("/devices")
class DevicesEndpoint(Resource):

    @staticmethod
    @api.response(200, 'Success', ApiModels.devices_response)
    def get():
        return get_all_devices()

    @staticmethod
    @api.doc(params={"name": "Name of device to add or update"}, body=ApiModels.device_fields)
    @api.response(204, 'Success')
    @api.response(400, 'Must provide device name to add/update service')
    def put():
        name = request.args.get("name")
        if not name:
            return "Must provide device name to add/update device", 400

        device = request.get_json()
        set_device(device)
        return {}, 204


@api.route("/services")
class ServicesEndpoint(Resource):

    @staticmethod
    @api.response(200, 'Success', [ApiModels.services_response])
    def get():
        return get_all_services()

    @staticmethod
    @api.doc(params={"name": "Name of service to add or update"}, body=ApiModels.service_fields)
    @api.response(204, 'Success')
    @api.response(400, 'Must provide service name to add/update service')
    def put():
        name = request.args.get("name")
        if not name:
            return "Must provide service name to add/update service", 400

        service = request.get_json()
        set_service(service)
        return {}, 204


@api.route("/scan")
class ScanEndpoint(Resource):

    @staticmethod
    @api.doc(params={"token": "The token returned from the corresponding POST that initiated the portscan",
                     "target": "The target for the portscan request"})
    @api.response(200, 'Success', ApiModels.portscan_data)
    @api.response(400, "Must provide token and target to get portscan")
    def get():
        target = request.args.get("target")
        if not target:
            return "Must provide target to get portscan", 400
        token = request.args.get("token")
        if not token:
            return "Must provide token to get portscan", 400

        return get_portscan(target, token)

    @staticmethod
    @api.doc(params={"target": "IP address or hostname of target host or device to scan"})
    @api.response(200, 'Success', ApiModels.token_response)
    @api.response(400, 'Must provide target to get portscan')
    def post():
        target = request.args.get("target")
        if not target:
            return "Must provide target to initiate portscan", 400
        token = start_portscan(target)
        return {"token": token}


@api.route("/worker/portscan")
class WorkerScanEndpoint(Resource):

    @staticmethod
    @api.doc(body=ApiModels.portscan_data)
    @api.response(204, 'Success')
    def post():
        portscan_data = request.get_json()
        record_portscan_data(portscan_data)

        return {}, 204


@api.route("/traceroute")
class TracerouteEndpoint(Resource):

    @staticmethod
    @api.doc(params={"token": "The token returned from the corresponding POST that initiated the traceroute",
                     "target": "The target for the traceroute request"})
    @api.response(400, "Must provide token and target to get traceroute")
    @api.response(200, 'Success', ApiModels.traceroute_data)
    def get():

        target = request.args.get("target")
        if not target:
            return "Must provide service target to get traceroute", 400
        hostname = get_hostname_from_target(target)

        token = request.args.get("token")
        if not token:
            return "Must provide token to get traceroute", 400
        return get_traceroute(hostname, token)

    @staticmethod
    @api.doc(params={"target": "IP address or hostname of target service, host, or device to find traceroute for"})
    @api.response(200, 'Success', ApiModels.token_response)
    @api.response(400, 'Must provide target to initiate traceroute')
    def post():
        target = request.args.get("target")
        if not target:
            return "Must provide  target to get traceroute", 400
        hostname = get_hostname_from_target(target)

        token = start_traceroute(hostname)
        return {"token": token}


@api.route("/worker/traceroute")
class WorkerTracerouteEndpoint(Resource):

    @staticmethod
    @api.doc(body=ApiModels.traceroute_data)
    @api.response(204, 'Success')
    def post():
        traceroute_data = request.get_json()
        record_traceroute_data(traceroute_data)

        return {}, 204


@api.route("/capture")
class CaptureEndpoint(Resource):

    @staticmethod
    @api.doc(params={"ip": "The ip address for which to capture packets",
                     "protocol": "The protocol for which to capture packets",
                     "port": "The port for which to capture packets",
                     "num_packets": "The number of packets to retrieve"})
    @api.response(200, 'Success', ApiModels.capture_data)
    def get():

        ip = request.args.get("ip")
        protocol = request.args.get("protocol")
        port = request.args.get("port")
        num_packets = request.args.get("num_packets")

        if ip: ip = get_ip_address_from_target(ip)

        if not num_packets or not num_packets.isnumeric(): num_packets = 10
        if port and port.isnumeric(): port = int(port)
        else: port = None

        return {"packets": get_capture(ip, protocol, port, int(num_packets))}

    @staticmethod
    @api.doc(params={"ip": "The ip address for which to capture packets",
                     "protocol": "The protocol for which to capture packets",
                     "port": "The port for which to capture packets",
                     "capture_time": "The time to capture packets"})
    @api.response(200, 'Capture initiated')
    def post():

        ip = request.args.get("ip")
        protocol = request.args.get("protocol")
        port = request.args.get("port")
        capture_time = request.args.get("capture_time")

        if ip: ip = get_ip_address_from_target(ip)

        if not capture_time: capture_time = 180
        else:  capture_time = int(capture_time)

        start_capture(ip, protocol, port, capture_time)
        return "Capture initiated", 200


@api.route("/worker/capture")
class WorkerCaptureEndpoint(Resource):

    @staticmethod
    @api.doc(body=ApiModels.capture_data)
    @api.response(204, 'Success')
    def post():
        capture_data = request.get_json()
        record_capture_data(capture_data)

        return {}, 204
