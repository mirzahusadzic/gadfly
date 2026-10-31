/** The reader's colours: Light, or one of After the Poem's three studies,
 * Dusk & apricot (the default), Paper & iris and Watermelon & mint. The
 * choice is kept in the browser under KEY and applied as the page's
 * data-theme, with VitePress's dark class for the dark studies. The page head
 * applies it before the first paint (HEAD below); this keeps it current. */
import { computed, ref } from 'vue';

export const KEY = 'gadfly-theme';
export const THEMES = [
  { id: 'light', name: 'Light', about: 'White paper and blue links' },
  { id: 'daylight', name: 'Paper & iris', about: 'Airy lavender and warm peach' },
  { id: 'dusk', name: 'Dusk & apricot', about: 'Plum, lilac, a little butter yellow' },
  { id: 'play', name: 'Watermelon & mint', about: 'Ripe berry, fresh mint, coral' },
];
const IDS = THEMES.map((theme) => theme.id);
const DEFAULT = 'dusk';
const DARK = ['dusk', 'play'];

/** The same rule, run in the page head before anything is drawn. */
export const HEAD = `(() => {
  let theme = '${DEFAULT}';
  try {
    const kept = localStorage.getItem('${KEY}');
    if (${JSON.stringify(IDS)}.includes(kept)) theme = kept;
  } catch {}
  document.documentElement.dataset.theme = theme;
  document.documentElement.classList.toggle('dark', ${JSON.stringify(DARK)}.includes(theme));
})();`;

const choice = ref(DEFAULT);
const isDark = computed(() => DARK.includes(choice.value));
let started = false;

function apply() {
  document.documentElement.dataset.theme = choice.value;
  document.documentElement.classList.toggle('dark', isDark.value);
}

/** Call from a component's onMounted: reads the kept choice. */
export function startTheme() {
  if (started) return;
  started = true;
  try {
    const kept = localStorage.getItem(KEY);
    if (IDS.includes(kept)) choice.value = kept;
  } catch {}
  apply();
}

export function choose(id) {
  choice.value = id;
  try {
    localStorage.setItem(KEY, id);
  } catch {}
  apply();
}

export const useTheme = () => ({ choice, isDark, choose });
