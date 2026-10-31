import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { TokenVault } from '../src/main/auth/vault';
import {
  validClientId,
  validateVerificationUri,
  exchangeMinecraftToken,
  MicrosoftLogin,
} from '../src/main/auth/microsoft';
test('Client ID e endereço de autorização são estritamente validados', () => {
  assert.equal(validClientId(null), false);
  assert.equal(validClientId('00000000-0000-0000-0000-000000000000'), false);
  assert.equal(validClientId('not-a-client'), false);
  assert.equal(
    validateVerificationUri('https://microsoft.com/devicelogin'),
    'https://microsoft.com/devicelogin',
  );
  for (const uri of [
    'http://microsoft.com/devicelogin',
    'https://evil.invalid/',
    'https://microsoft.com.evil.invalid/devicelogin',
    'https://microsoft.com/devicelogin?code=evil',
  ])
    assert.throws(() => validateVerificationUri(uri));
});
test('vault escreve somente cifra e não grava quando cofre seguro está indisponível', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'atlas-vault-'));
  try {
    const path = join(dir, 'account.bin');
    const cipher = {
      available: () => true,
      encrypt: (v: string) => Buffer.from(v.split('').reverse().join('')),
      decrypt: (v: Buffer) => v.toString().split('').reverse().join(''),
    };
    const vault = new TokenVault(path, cipher);
    await vault.write('PRIVATE_TEST_TOKEN');
    assert.equal(await vault.read(), 'PRIVATE_TEST_TOKEN');
    assert.equal((await readFile(path)).includes(Buffer.from('PRIVATE_TEST_TOKEN')), false);
    await vault.clear();
    await assert.rejects(stat(path));
    const disabled = new TokenVault(path, { ...cipher, available: () => false });
    await disabled.write('PRIVATE_TEST_TOKEN');
    assert.equal(await disabled.read(), undefined);
    await assert.rejects(stat(path));
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
test('cadeia Microsoft/Xbox valida perfil real sem expor tokens no estado público', async () => {
  const responses = [
    { Token: 'xbox-test-token' },
    { Token: 'device-test-token', NotAfter: '2099-01-01T00:00:00Z' },
    { Token: 'xsts-test-token', DisplayClaims: { xui: [{ uhs: 'test-hash' }] } },
    { access_token: 'game-test-token', expires_in: 3600 },
    { id: 'a'.repeat(32), name: 'AtlasTest' },
  ];
  const urls: string[] = [];
  const request = async (url: any, init: any) => {
    urls.push(url);
    assert.equal(init.redirect, 'error');
    if (url === 'https://device.auth.xboxlive.com/device/authenticate')
      assert.ok(init.headers.Signature);
    if (url === 'https://xsts.auth.xboxlive.com/xsts/authorize')
      assert.equal(JSON.parse(init.body).Properties.DeviceToken, 'device-test-token');
    return new Response(JSON.stringify(responses.shift()), {
      headers: { 'Content-Type': 'application/json' },
    });
  };
  const session = await exchangeMinecraftToken('microsoft-test-token', request as typeof fetch);
  assert.equal(session.profile.name, 'AtlasTest');
  assert.equal(session.accessToken, 'game-test-token');
  assert.equal(JSON.stringify(session.profile).includes('token'), false);
  assert.deepEqual(urls, [
    'https://user.auth.xboxlive.com/user/authenticate',
    'https://device.auth.xboxlive.com/device/authenticate',
    'https://xsts.auth.xboxlive.com/xsts/authorize',
    'https://api.minecraftservices.com/authentication/login_with_xbox',
    'https://api.minecraftservices.com/minecraft/profile',
  ]);
});
test('sem aplicativo Microsoft não há login fictício nem sessão para jogar', async () => {
  const vault = new TokenVault('/unused-test', {
    available: () => false,
    encrypt: () => Buffer.alloc(0),
    decrypt: () => '',
  });
  const auth = new MicrosoftLogin(null, vault);
  assert.equal(auth.publicState().configured, false);
  await assert.rejects(auth.signIn(), /Cadastre/);
  await assert.rejects(auth.forGame());
  assert.equal(auth.publicState().account, undefined);
});
test('falha Xbox não retorna corpo remoto nem tokens como erro para o jogador', async () => {
  await assert.rejects(
    exchangeMinecraftToken(
      'secret-test',
      async () => new Response('RAW_REMOTE_TEST_SECRET', { status: 401 }),
    ),
    (error) => error instanceof Error && !error.message.includes('RAW_REMOTE_TEST_SECRET'),
  );
});

test('logout vence uma gravação de cache concorrente', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'atlas-vault-race-'));
  try {
    const path = join(dir, 'account.bin');
    const cipher = {
      available: () => true,
      encrypt: (value: string) => Buffer.from('CIPHER-' + value),
      decrypt: (bytes: Buffer) => bytes.toString().slice(7),
    };
    const vault = new TokenVault(path, cipher);
    const writing = vault.write('TOKEN_TEST');
    const clearing = vault.clear();
    await Promise.all([writing, clearing]);
    assert.equal(await vault.read(), undefined);
    await assert.rejects(stat(path));
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
