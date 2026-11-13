// @nook/kit: the shared design system and front-end bricks for every Nook app.
// Styles are a separate import:  import '@nook/kit/styles.css'
// Icons (lucide):                 import { Film } from '@nook/kit/icons'

export { NookProvider, AppShell, Scene } from './components/Shell.jsx';
export { Button, IconButton } from './components/Button.jsx';
export { Field, Input, Select } from './components/Field.jsx';
export { Segmented } from './components/Segmented.jsx';
export { Card, CardHead, Chip, Badge, Stat, Progress, Empty, Alert } from './components/Bits.jsx';
export { Sheet, useConfirm } from './components/Sheet.jsx';
export { useToast } from './components/Toast.jsx';
export { useContextMenu, usePageMenu } from './components/Menu.jsx';
export { useIdle, IdleBadge, IdleWarning, leaveApps, useStillHere } from './components/Idle.jsx';
export { Speech } from './components/Speech.jsx';
export { Confetti } from './components/Confetti.jsx';

export { Mascot, Sprite } from './mascot/Mascot.jsx';
export { compose, MOODS, EYES, MOUTHS } from './mascot/sprite.js';

export { spring, ease, rise, pop, stagger, lift, press } from './motion.js';
export { personaVars, applyPersona, say, partOfDay } from './persona.js';
export { api, getJSON, postJSON, fileToBase64, store, ApiError } from './api.js';
export { useTypewriter, useInterval, usePoll, useStoredState, useFlash } from './hooks.js';

export const KIT_VERSION = '1.5.1';
