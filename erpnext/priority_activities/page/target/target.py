// you will need to install via 'npm install jsonwebtoken' or in your package.json

var jwt = require("jsonwebtoken");

var METABASE_SITE_URL = "https://erp.ns.bt";
var METABASE_SECRET_KEY = "8e8db02d3fdc1c5ae4252b4b9cdc036c9050f7c86659fce6ba043f7bcfe833d4";

var payload = {
  resource: { question: 88 },
  params: {},
  exp: Math.round(Date.now() / 1000) + (10 * 60) // 10 minute expiration
};
var token = jwt.sign(payload, METABASE_SECRET_KEY);

var iframeUrl = METABASE_SITE_URL + "/embed/question/" + token + "#bordered=true&titled=true";