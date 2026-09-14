import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = dirname(currentDirectory);
const collection = JSON.parse(
  readFileSync(join(currentDirectory, 'Routes-API.postman_collection.json'), 'utf8'),
);
const environment = JSON.parse(
  readFileSync(join(currentDirectory, 'Local.postman_environment.json'), 'utf8'),
);

assert.match(collection.info.schema, /collection\/v2\.1\.0/);
assert.equal(environment.values.find((item) => item.key === 'base_url')?.enabled, true);

const requests = [];
function collect(items) {
  for (const item of items) {
    if (item.request) requests.push(item);
    if (item.item) collect(item.item);
  }
}
collect(collection.item);

assert.equal(requests.length, 13, 'La colección debe contener 13 solicitudes.');
assert.equal(new Set(requests.map((item) => item.name)).size, requests.length);
for (const item of requests) {
  assert.ok(item.request.url.raw.startsWith('{{base_url}}/'));
  assert.ok(
    item.event?.some((event) => event.listen === 'test' && event.script?.exec?.length),
    `${item.name} no contiene pruebas automáticas.`,
  );
  for (const event of item.event ?? []) {
    assert.doesNotThrow(
      () => new Function(event.script.exec.join('\n')),
      `${item.name} contiene JavaScript inválido en ${event.listen}.`,
    );
  }
  if (item.request.body?.mode === 'raw') {
    const resolvedBody = item.request.body.raw.replace(/\{\{[^}]+\}\}/g, '1');
    assert.doesNotThrow(() => JSON.parse(resolvedBody), `${item.name} contiene un body JSON inválido.`);
  }
  for (const field of item.request.body?.formdata ?? []) {
    if (field.type === 'file') {
      assert.ok(existsSync(join(projectRoot, field.src)), `${field.src} no existe.`);
    }
  }
}

const contracts = new Set(requests.map((item) => `${item.request.method} ${item.request.url.raw}`));
for (const contract of [
  'GET {{base_url}}/health/',
  'POST {{base_url}}/routes/import/',
  'GET {{base_url}}/routes/?page=1&page_size=25&ordering=-created_at',
  'POST {{base_url}}/routes/',
  'GET {{base_url}}/routes/{{route_id}}/',
  'POST {{base_url}}/routes/execute/',
  'GET {{base_url}}/routes/{{route_id}}/logs/',
]) {
  assert.ok(contracts.has(contract), `Falta el contrato ${contract}.`);
}

console.log(`Colección válida: ${requests.length} solicitudes con pruebas automáticas.`);
