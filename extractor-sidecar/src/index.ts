import { createServer } from "node:http";

import { createApp } from "./app.js";
import { loadConfig } from "./config.js";

const config = loadConfig();
const app = createApp(config);
const server = createServer(app);

server.listen(config.listenPort, "0.0.0.0", () => {
  console.log(
    `[extractor-sidecar] listening on 0.0.0.0:${config.listenPort}`,
  );
});
