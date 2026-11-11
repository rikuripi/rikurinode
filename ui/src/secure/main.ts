import { mount } from 'svelte';
import '../fonts.css';
import '../theme.css';
import Secure from './Secure.svelte';

const target = document.getElementById('app');
if (target) mount(Secure, { target });
