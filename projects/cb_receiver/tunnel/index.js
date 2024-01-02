import localtunnel from 'localtunnel';
import { readFileSync, writeFileSync } from 'fs';
import { parse, stringify } from 'envfile';


(async () => {
  const port = process.argv.splice(2)[0] || 8000;
  try {
    console.log('Opening a tunnel...');
    const tunnel = await localtunnel({ port: port, subdomain: 'mtest' });

    console.log(`\nPublic url: ${tunnel.url}`);

    const sourcePath = '../.env'
    const data = readFileSync(sourcePath, 'utf8');
    const parsedFile = parse(data);
    parsedFile.SERVER_URL = '"' + tunnel.url + '/"';
    writeFileSync(sourcePath, stringify(parsedFile))

    tunnel.on('close', () => {
      console.warn('WARNING: Tunnel closed!');
    });
  } catch (error) {
    console.error(`Error: ${error}`);
  }
})();
