import base64
import viktor as vkt
from app.data_exchange import list_exchanges_in_hub
from app.crud import get_hubs, get_elements_categories, get_exchange_file_urn
from app.views import APSView, APSresult
import asyncio


class Parametrization(vkt.Parametrization):
    input = vkt.Text(" # Dx - APS - VIKTOR Agent")

class Controller(vkt.Controller):
    parametrization = Parametrization
    
    @staticmethod
    def run(params, **kwargs) -> str:
        # integration = vkt.external.OAuth2Integration("aps-integration-1")
        # token = integration.get_access_token()
        # # Run async orchestrator in a fresh event loop
        # hubs = get_hubs(token=token)
        # exchanges = asyncio.run(list_exchanges_in_hub(hub_id=hubs[0].id, token = token))
        # elevated_pavilion_house_id = "ZXhjfndsMzdxWDE1MHczcTJLTXN1YTFFR3hfTDJDfjQzOTdjMGM1LWVhM2EtMzg1YS04NzE1LWEwZDczOTE3MjQ1ZQ"
        # building_categories = get_elements_categories(token=token, exchange_id=elevated_pavilion_house_id)
        # urn = building_categories["Elevated Pavilion House"]
        # content = asyncio.run(get_all_content_from_all_hubs(token=token))
        return print("hello!")
    
    @APSView("Model Viewer", duration_guess=40)
    def show_cad_model(self, params, **kwargs):
        # 1. Get 3‑legged token from VIKTOR integration
        integration = vkt.external.OAuth2Integration("aps-integration-1")
        token = integration.get_access_token()
        # Run async orchestrator in a fresh event loop
        hubs = get_hubs(token=token)
        exchanges = asyncio.run(list_exchanges_in_hub(hub_id=hubs[0].id, token = token))
        print(exchanges)
        dx_id = exchanges["Commercial_Building_Design"]
        # elevated_pavilion_house_id = "ZXhjfndsMzdxWDE1MHczcTJLTXN1YTFFR3hfTDJDfjQzOTdjMGM1LWVhM2EtMzg1YS04NzE1LWEwZDczOTE3MjQ1ZQ"
        # building_categories = get_elements_categories(token=token, exchange_id=elevated_pavilion_house_id)
        urn = get_exchange_file_urn(token=token, exchange_id=dx_id)
        # print(urn)
        # urn:adsk.wipprod:dm.lineage:QHwK9k2_RCmaNRhs7-Lxeg
        # "urn:adsk.wipprod:fs.file:vf.QHwK9k2_RCmaNRhs7-Lxeg?version=1"
        # urn = "urn:adsk.wipprod:fs.file:vf.QHwK9k2_RCmaNRhs7-Lxeg?version=1"
        # encoded_urn = base64.urlsafe_b64encode(urn.encode()).decode().rstrip("=")

        # urn = "urn:adsk.wipprod:fs.file:vf.QHwK9k2_RCmaNRhs7-Lxeg?version=1"
        print(f"{urn=}")
        urn_bs64 = base64.urlsafe_b64encode(urn.encode()).decode().rstrip("=")
        return APSresult(urn_b64=urn_bs64 , token=token)
        # return APSresult(urn_b64="dXJuOmFkc2sud2lwcHJvZDpmcy5maWxlOnZmLlFId0s5azJfUkNtYU5SaHM3LUx4ZWc_dmVyc2lvbj0x", token=token)
    
    @staticmethod
    def to_b64url(value: str) -> str:
        return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")