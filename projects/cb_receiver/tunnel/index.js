import { readFileSync, writeFileSync, existsSync } from 'fs';
import { parse, stringify } from 'envfile';
import { tunnelmole } from 'tunnelmole';
import { resolve } from 'path';

(async () => {
  const port = process.argv[2] || 8000;
  const envPath = resolve(process.argv[3] || '../.env')

  console.info('Opening a new tunnel...');
  const url = await tunnelmole({ port: port });
  console.info(`\nPublic url: ${url}\n`);

  let envContent;
  if (!existsSync(envPath)) {
    console.warn(`WARNING: File '${envPath}' not found, creating a new one.`);
    envContent = `SERVER_URL=${url}`;
  } else {
    const oldEnvData = readFileSync(envPath, 'utf8');
    const parsedFile = parse(oldEnvData);
    parsedFile.SERVER_URL = url;
    envContent = stringify(parsedFile);
  }
  writeFileSync(envPath, envContent);
  console.info(`Variable 'SERVER_URL' has been saved in '${envPath}'.`);
})();
