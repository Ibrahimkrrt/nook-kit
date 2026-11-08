import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@nook/kit/styles.css';
import './app.css';
import { NookProvider } from '@nook/kit';
import persona from './persona.json';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <NookProvider persona={persona}>
      <App />
    </NookProvider>
  </StrictMode>,
);
