import { test } from 'node:test';
import assert from 'node:assert/strict';
import { exchangeMinecraftToken } from '../src/main/auth/microsoft';
import { AuthFlowError, publicAuthError } from '../src/main/auth/errors';
const stages = [
  'Xbox Live',
  'Xbox dispositivo',
  'Xbox XSTS',
  'Minecraft autorização',
  'Minecraft perfil',
];
for (let failed = 0; failed < stages.length; failed++) {
  test(`failure at ${stages[failed]} reports its stage and status without remote secrets`, async () => {
    const responses = [
      { Token: 'xbox-fixture' },
      { Token: 'device-fixture', NotAfter: '2099-01-01T00:00:00Z' },
      { Token: 'xsts-fixture', DisplayClaims: { xui: [{ uhs: 'fixture' }] } },
      { access_token: 'game-fixture', expires_in: 3600 },
      { id: 'a'.repeat(32), name: 'FixturePlayer' },
    ];
    let call = 0;
    const status = failed === 4 ? 404 : failed === 3 ? 403 : 401;
    const request = async () => {
      const current = call++;
      return new Response(
        JSON.stringify(
          current === failed
            ? { errorMessage: 'REMOTE_SECRET_TOKEN_DO_NOT_ECHO' }
            : responses[current],
        ),
        { status: current === failed ? status : 200 },
      );
    };
    await assert.rejects(
      exchangeMinecraftToken('PRIVATE_FIXTURE', request as typeof fetch),
      (error) => {
        assert.ok(error instanceof AuthFlowError);
        const message = publicAuthError(error);
        assert.ok(message.includes(stages[failed]));
        assert.ok(message.includes(String(status)));
        assert.doesNotMatch(message, /REMOTE_SECRET|PRIVATE_FIXTURE/);
        if (failed === 3) assert.match(message, /aprovação/);
        return true;
      },
    );
  });
}
test('unknown errors never expose an arbitrary MSAL message or remote token', () => {
  assert.doesNotMatch(publicAuthError(new Error('access_token=SECRET_FIXTURE')), /SECRET_FIXTURE/);
  assert.match(
    publicAuthError({ errorCode: 'invalid_client', errorMessage: 'SECRET_FIXTURE' }),
    /cliente público/,
  );
  assert.match(publicAuthError(new AuthFlowError('Xbox XSTS', 401, 2148916233)), /perfil Xbox/);
});
