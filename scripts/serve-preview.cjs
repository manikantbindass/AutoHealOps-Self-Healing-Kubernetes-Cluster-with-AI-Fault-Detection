/* Native preview for the compiled React bundle; production uses nginx. */
const http = require('http');
const net = require('net');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../frontend/build');
const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml','.json':'application/json','.ico':'image/x-icon'};
const server = http.createServer((req,res) => {
  if (req.url.startsWith('/api/')) {
    const proxy = http.request({hostname:'127.0.0.1',port:Number(process.env.BACKEND_PORT || 8000),path:req.url,method:req.method,headers:req.headers}, upstream=>{res.writeHead(upstream.statusCode,upstream.headers);upstream.pipe(res);});
    proxy.on('error',()=>{res.writeHead(502);res.end('Backend unavailable');});
    req.pipe(proxy); return;
  }
  let file;
  try { file = path.resolve(root, '.' + decodeURIComponent(req.url.split('?')[0])); } catch {res.writeHead(400);res.end();return;}
  if (file !== root && !file.startsWith(root + path.sep)) {res.writeHead(403);res.end();return;}
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) file=path.join(root,'index.html');
  if (!fs.existsSync(file)) {res.writeHead(503);res.end('Build frontend first: npm run build');return;}
  res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','X-Content-Type-Options':'nosniff'});
  fs.createReadStream(file).pipe(res);
});
server.on('upgrade',(req,socket,head)=>{
  if (!req.url.startsWith('/api/v1/ws')) return socket.destroy();
  const upstream=net.connect(Number(process.env.BACKEND_PORT || 8000),'127.0.0.1',()=>{
    upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n`+req.rawHeaders.reduce((s,h,i,a)=>i%2?s:s+`${h}: ${a[i+1]}\r\n`,'')+'\r\n');
    if(head.length)upstream.write(head); socket.pipe(upstream);upstream.pipe(socket);
  });
  upstream.on('error',()=>socket.destroy());socket.on('error',()=>upstream.destroy());
});
server.listen(Number(process.env.DASHBOARD_PORT || 3000),'127.0.0.1',()=>console.log('AutoHealOps compiled preview started'));
