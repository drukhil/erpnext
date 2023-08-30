def dash_test():
        import jwt
        import time

        METABASE_SITE_URL = "https://erp.ns.bt/metabase"
        METABASE_SECRET_KEY = "8e8db02d3fdc1c5ae4252b4b9cdc036c9050f7c86659fce6ba043f7bcfe833d4"

        payload = {
          "resource": {"dashboard": 10},
          "params": {

          }
        }
        token = jwt.encode(payload, METABASE_SECRET_KEY, algorithm="HS256")

        iframeUrl = METABASE_SITE_URL + "/embed/dashboard/" + token + "#theme=night&bordered=true&titled=true"
        print(iframeUrl)
