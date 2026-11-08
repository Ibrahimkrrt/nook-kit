import { useEffect, useState } from 'react';
import { AppShell, Card, CardHead, Mascot, Speech, api, say, useFlash } from '@nook/kit';
import persona from './persona.json';

const backend = api('/api/__ID__');

export default function App() {
  const [hello, setHello] = useState(null);
  const [reaction, flash] = useFlash();

  useEffect(() => {
    backend.get('/hello').then(setHello).catch(() => setHello(null));
  }, []);

  return (
    <AppShell persona={persona}>
      <Card tone="accent" animate className="app-hero">
        <Mascot
          def={persona.mascot} mood={reaction?.mood || 'idle'} size={128} vt="mascot-__ID__"
          onPoke={() => flash({ mood: 'happy', text: say(persona, 'poke') })}
        />
        <Speech text={reaction?.text || say(persona, 'hello')} />
      </Card>
      <Card animate>
        <CardHead eyebrow="Back end" title="It's alive" />
        <p className="nk-muted">{hello ? hello.hello : 'Waiting for /api/__ID__/hello…'}</p>
      </Card>
    </AppShell>
  );
}
