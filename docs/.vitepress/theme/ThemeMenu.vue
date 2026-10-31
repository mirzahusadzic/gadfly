<script setup>
/** The colour menu, After the Poem's: the top bar shows the current study's
 * swatch and opens a small sheet, "Find the mood.", with a card for each
 * study; with `inline`, the same cards sit in the phone's menu screen.
 * The arrow keys move through the themes and show each one; Enter or a click
 * keeps it and closes; Escape closes and goes back to the theme it opened on.
 * Focus returns to the button. */
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { THEMES, startTheme, useTheme } from './theme.js';

const props = defineProps({ inline: Boolean });
const { choice, choose } = useTheme();
const id = props.inline ? 'gf-theme-screen' : 'gf-theme-bar';
const open = ref(false);
const root = ref(null);
const button = ref(null);
let openedOn = null;

function show() {
  openedOn = choice.value;
  open.value = true;
  nextTick(() => root.value.querySelector('input:checked')?.focus());
}

function hide(refocus) {
  if (props.inline || !open.value) return;
  open.value = false;
  if (refocus) button.value?.focus();
}

function onKey(event) {
  if (props.inline || (event.key !== 'Enter' && event.key !== 'Escape')) return;
  event.preventDefault();
  if (event.key === 'Escape' && choice.value !== openedOn) choose(openedOn);
  hide(true);
}

// A click on a card keeps its theme and closes; the arrow keys also click the
// radio itself, and those keep the menu open.
const onCard = (event) => event.target.tagName !== 'INPUT' && hide(true);
const onFocusOut = (event) => !root.value.contains(event.relatedTarget) && hide(false);
const onOutside = (event) => !root.value?.contains(event.target) && hide(false);

onMounted(() => {
  startTheme();
  document.addEventListener('click', onOutside);
});
onBeforeUnmount(() => document.removeEventListener('click', onOutside));
</script>

<template>
  <div ref="root" class="gf-theme" :class="{ inline }" @focusout="onFocusOut">
    <button
      v-if="!inline"
      ref="button"
      type="button"
      class="gf-theme-button"
      title="Colour studies"
      :aria-expanded="open"
      :aria-controls="id"
      @click="open ? hide(true) : show()"
    >
      <span class="gf-dots" aria-hidden="true"><i /><i /><i /></span>
      <span class="gf-theme-label">Colours</span>
    </button>
    <div
      v-show="inline || open"
      :id="id"
      class="gf-theme-menu"
      @keydown="onKey"
      @mousedown="!inline && $event.target.tagName !== 'INPUT' && $event.preventDefault()"
    >
      <p class="gf-theme-title" :id="`${id}-title`">Find the mood.</p>
      <p class="gf-theme-intro">Four studies. The same material, seen in a different light.</p>
      <div class="gf-theme-cards" role="radiogroup" :aria-labelledby="`${id}-title`">
        <label v-for="theme in THEMES" :key="theme.id" class="gf-theme-card" @click="onCard">
          <input
            type="radio"
            :name="id"
            :value="theme.id"
            :checked="choice === theme.id"
            @change="choose(theme.id)"
          />
          <span class="gf-dots" :data-theme="theme.id" aria-hidden="true"><i /><i /><i /></span>
          <span class="gf-theme-name">
            {{ theme.name }}
            <small>{{ theme.about }}</small>
          </span>
        </label>
      </div>
    </div>
  </div>
</template>
