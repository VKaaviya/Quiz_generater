const http = require("http");
const fs   = require("fs");
const path = require("path");
const PORT = 3000;
const MIME = { ".html":"text/html", ".css":"text/css", ".js":"application/javascript" };
const server = http.createServer((req, res) => {
  const filePath = path.join(__dirname, "public", req.url === "/" ? "index.html" : req.url);
  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); return res.end("Not found"); }
    res.writeHead(200, { "Content-Type": MIME[path.extname(filePath)] || "text/plain" });
    res.end(data);
  });
});
server.listen(PORT, () => {
  console.log(`\n  Peblo → http://localhost:${PORT}\n`);
});
