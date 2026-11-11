import { mount } from 'svelte';
import '../fonts.css';
import '../theme.css';
import Cert from './Cert.svelte';

const target = document.getElementById('app');
if (target) mount(Cert, { target });
