from concurrent import futures
import time
import logging
import grpc
from libs import rpc_api, rpc_pb2, rpc_pb2_grpc
from umbral import keys, config, pre
from umbral.curve import Curve

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ReProxy(rpc_pb2_grpc.ReProxyServicer):

    def Encrypt(self, request, context):
        encrypt_text, capsule = rpc_api.UmbralApi.encrypt_by_pk(
            keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.pk)),
            str.encode(request.text))
        return rpc_pb2.EncryptReply(message=encrypt_text.hex(), capsule=capsule.to_bytes().hex())

    def Decrypt(self, request, context):
        sk = keys.UmbralPrivateKey.from_bytes(bytes.fromhex(request.sk))
        encrypt_text = bytes.fromhex(request.text)
        cpk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.cpk))
        ppk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.ppk))
        capsule = rpc_api.pre.Capsule.from_bytes(bytes.fromhex(request.capsule),
                                                 rpc_api.pre.UmbralParameters(Curve(714)))
        flags = request.flags
        kFrags = list()
        for flag in flags:
            kFrags.append(pre.KFrag.from_bytes(bytes.fromhex(flag)))
        text = rpc_api.UmbralApi.decrypt_by_sk(sk, cpk, ppk, encrypt_text, capsule, kFrags)
        return rpc_pb2.DecryptReply(text=text)

    def GetKFlags(self, request, context):
        sk = keys.UmbralPrivateKey.from_bytes(bytes.fromhex(request.sk))
        cpk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.pk))
        k_frags, proxy_pk = rpc_api.UmbralApi.generate_k_flags(sk, cpk)
        cFrags = []
        for kFrag in k_frags:
            cFrags.append(kFrag.to_bytes().hex())
        return rpc_pb2.GetKFlagsReply(flags=cFrags, text=proxy_pk.hex())

    def Capsule(self, request, context):
        curve = rpc_api.pre.UmbralParameters(Curve(714))
        capsule = rpc_api.pre.Capsule.from_bytes(bytes.fromhex(request.capsule),
                                                 curve)
        flags = request.flags
        cpk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.cpk))
        rpk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.rpk))
        ppk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(request.ppk))
        kFrags = list()
        for flag in flags:
            kFrags.append(pre.KFrag.from_bytes(bytes.fromhex(flag)))
        text = rpc_api.UmbralApi.capsule_attach(capsule, kFrags, cpk, rpk, ppk)
        return rpc_pb2.CapsuleReply(text=text.hex())


def serve():
    config.set_default_curve()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rpc_pb2_grpc.add_ReProxyServicer_to_server(ReProxy(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Nucypher server start :50052")
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    logging.basicConfig()
    serve()
