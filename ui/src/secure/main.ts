// The secure bundle's pages, picked by path; the control plane serves this
// same page at /, /setup, /claim, /signin, /home and /name, over TLS only (src/ui.rs).
import { mount, type Component } from 'svelte';
import '../fonts.css';
import '../theme.css';
import Claim from './Claim.svelte';
import Home from './Home.svelte';
import Name from './Name.svelte';
import Secure from './Secure.svelte';
import SignIn from './SignIn.svelte';

const PAGES: Record<string, Component> = { '/claim': Claim, '/signin': SignIn, '/home': Home, '/name': Name };

const target = document.getElementById('app');
if (target) mount(PAGES[location.pathname] ?? Secure, { target });
