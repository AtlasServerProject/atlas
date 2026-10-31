"""Idempotent registration reconciliation. Never trusts unowned remote entries."""
import hashlib
from zoneinfo import ZoneInfo
from challonge import ApiError, body

class Review(Exception):
    pass

def marker(event, player):
    return 'atlas:' + hashlib.sha256((str(event) + ':' + str(player)).encode()).hexdigest()

def remote_state(remote):
    a = remote['attributes']
    return a.get('state') or a.get('states', {}).get('state')

class Service:
    def __init__(self, repository, client):
        self.repo, self.api = repository, client

    def sync(self, event):
        if not self.repo.current(event):
            return
        capacity = event['capacity']
        title = event['title']
        path = '/tournaments/' + str(event.get('remote_id') or event['slug'])
        try:
            remote = self.api.call('GET', path + '.json')['data']
        except ApiError as error:
            if error.status != 404 or event['state'] != 'CREATING':
                raise
            remote = self.api.call('POST', '/tournaments.json', body('tournament', name=event['title'], url=event['slug'],
                tournament_type='single elimination', game_name='Pokémon', private=False,
                description=title + '. Formato Atlas baseado na Gen 9. Batalhas no Minecraft. Inscrições pelo comando /torneio entrar. A equipe informa as regras e acompanha os resultados.',
                registration_options={'open_signup':False,'signup_cap':capacity},
                group_stage_enabled=False))['data']
        rid = str(remote['id'])
        path = '/tournaments/' + rid
        state = remote_state(remote)
        if event['state'] == 'CREATING':
            if state != 'pending':
                raise Review('Estado externo inesperado na abertura')
            self.repo.finish(event, rid, 'OPEN', f'{title} aberto! 0/{capacity} participantes. Use /torneio entrar. Prazo máximo: ' + event['registration_deadline'].astimezone(ZoneInfo('America/Fortaleza')).strftime('%d/%m %H:%M:%S') + ' (Brasília). Se não lotar, será cancelado.')
            return
        entries = self.repo.entries(event['id'])
        all_entries = self.repo.entries(event['id'], active=False)
        owned = {marker(event['id'], p['player_uuid']) for p in all_entries}
        desired = {marker(event['id'], p['player_uuid']):p for p in entries}
        participants = self.api.call('GET', path + '/participants.json?page=1&per_page=100')['data']
        if not isinstance(participants, list) or len(participants) > capacity:
            raise Review('Quantidade externa inesperada')
        by_marker = {}
        for p in participants:
            m = p['attributes'].get('misc')
            if m not in owned or m in by_marker:
                raise Review('Participantes externos alterados; conferir no Challonge')
            by_marker[m] = p
        if state in ('underway','awaiting_review','complete'):
            if event['state'] != 'FULL' or len(desired) != capacity or set(by_marker) != set(desired):
                raise Review('Torneio externo iniciado com inscrições divergentes')
            self.repo.finish(event, rid, 'COMPLETE' if state == 'complete' else 'STARTED', 'Chaves do ' + title + ' disponíveis: https://challonge.com/' + event['slug'])
            return
        if state != 'pending':
            raise Review('Estado externo requer conferência')
        for m, p in by_marker.items():
            if m not in desired:
                self.api.call('DELETE', path + '/participants/' + str(p['id']) + '.json')
        # Hash of the random event UUID provides a stable draw across restarts.
        missing = [{'name':desired[m]['player_name'],'misc':m} for m in sorted(desired) if m not in by_marker]
        if missing:
            self.api.call('POST', path + '/participants/bulk_add.json', body('Participants', participants=missing))
        if not self.repo.current(event):
            return  # New local revision will reconcile the next snapshot.
        if event['state'] == 'FULL':
            if len(desired) != capacity:
                raise Review('Torneio cheio com inscrições divergentes')
            participants = self.api.call('GET', path + '/participants.json?page=1&per_page=100')['data']
            if len(participants) != capacity or {p['attributes'].get('misc') for p in participants} != set(desired):
                raise Review('Conferência final dos participantes falhou')
            ordered = {m:seed for seed,m in enumerate(sorted(desired),1)}
            for p in participants:
                seed = ordered[p['attributes']['misc']]
                if p['attributes'].get('seed') != seed:
                    self.api.call('PUT', path + '/participants/' + str(p['id']) + '.json', body('participant', seed=seed))
            verified = self.api.call('GET', path + '/participants.json?page=1&per_page=100')['data']
            if len(verified) != capacity or any(p['attributes'].get('seed') != ordered.get(p['attributes'].get('misc')) for p in verified):
                raise Review('Sorteio externo divergente; conferir posições')
            if not self.repo.current(event):
                return
            self.api.call('PUT', path + '/change_state.json', body('TournamentState', state='start'))
            confirmed = self.api.call('GET', path + '.json')['data']
            if remote_state(confirmed) not in ('underway','awaiting_review'):
                raise Review('Início externo ainda não confirmado')
            self.repo.finish(event, rid, 'STARTED', f'{capacity}/{capacity} confirmados! {title} — chaves sorteadas: https://challonge.com/' + event['slug'] + ' — aguarde as orientações da equipe para batalhar.')
        else:
            self.repo.finish(event, rid, 'OPEN')

    def tick(self):
        self.repo.expire()
        event = self.repo.next()
        if not event:
            return False
        try:
            self.sync(event)
        except Review as error:
            self.repo.fail(event, str(error), review=True)
        except ApiError as error:
            self.repo.fail(event, str(error), delay=86400 if error.status in (401,403,429) else 300)
        except Exception:
            self.repo.fail(event, 'Falha temporária de integração; nova tentativa automática', delay=300)
        return True
