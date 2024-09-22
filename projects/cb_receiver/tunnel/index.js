import { parse, stringify } from 'envfile';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';
import { tunnelmole } from 'tunnelmole';

(async () => {
  const port = process.argv[2] || 8000;
  const envPath = resolve(process.argv[3] || '../.env')

  console.info('Opening a new tunnel...');
  const url = await tunnelmole({ port: port });
  console.info(`\nPublic url: ${url}\n`);

  let envs = {};
  if (existsSync(envPath)) {
    envs = parse(readFileSync(envPath, 'utf8'));
  }

  envs.SERVER_URL = url;

  writeFileSync(envPath, stringify(envs));

  console.info(`'SERVER_URL' has been saved in '${envPath}'.`);
})();
