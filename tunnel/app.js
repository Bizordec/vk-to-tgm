const localtunnel = require('localtunnel');
const fs = require('fs'); 
const { parse, stringify } = require('envfile');


(async () => {
  const port = process.argv.splice(2)[0] || 8000;
  const tunnel = await localtunnel({ port: port, subdomain: 'mtest' });
  
  // the assigned public url for your tunnel
  // i.e. https://abcdefgjhij.localtunnel.me
  console.log(tunnel.url);

  const sourcePath = '../.env'
  const data = fs.readFileSync(sourcePath, 'utf8');
  const parsedFile = parse(data);
  parsedFile.SERVER_URL = '"' + tunnel.url + '/"';
  parsedFile.NGINX_HOST = '"' + tunnel.url.match(/https?:\/\/(.*)/)[1] + '"';
  fs.writeFileSync(sourcePath, stringify(parsedFile)) 

  tunnel.on('close', () => {
    console.warn('WARNING: Tunnel closed!');
  });
})();