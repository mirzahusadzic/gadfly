<script setup>
import { nextTick, onMounted, ref, watch } from 'vue';
import { draw } from './mermaid.js';
import { useTheme } from './theme.js';

const props = defineProps({ source: { type: String, required: true } });
const { isDark } = useTheme();
const svg = ref('');
const error = ref('');
const state = ref('pending');
const measure = ref(null);
const dialog = ref(null);
const expanded = ref(false);

async function render() {
  try {
    svg.value = await draw(decodeURIComponent(props.source), {
      dark: isDark.value,
      container: measure.value,
    });
    error.value = '';
    state.value = 'drawn';
  } catch (failure) {
    error.value = String(failure?.message ?? failure);
    state.value = 'failed';
  }
}

async function expand() {
  expanded.value = true;
  await nextTick();
  dialog.value.showModal();
}

onMounted(render);
watch(isDark, render);
</script>

<template>
  <figure class="diagram" :data-state="state">
    <template v-if="svg">
      <div class="diagram-preview" @click="expand" v-html="svg" />
      <button
        class="diagram-expand"
        type="button"
        title="Show the whole diagram"
        aria-label="Show the whole diagram"
        @click="expand"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7" />
        </svg>
      </button>
      <dialog
        ref="dialog"
        class="diagram-dialog"
        @click.self="dialog.close()"
        @close="expanded = false"
      >
        <button
          class="diagram-close"
          type="button"
          title="Close"
          aria-label="Close"
          @click="dialog.close()"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
        <div v-if="expanded" class="diagram-whole" v-html="svg" />
      </dialog>
    </template>
    <div v-else-if="error" class="diagram-error">
      <p>This diagram could not be drawn: {{ error }}</p>
      <pre><code>{{ decodeURIComponent(props.source) }}</code></pre>
    </div>
    <div v-else class="diagram-pending" aria-hidden="true" />
    <div ref="measure" class="diagram-measure" aria-hidden="true" />
  </figure>
</template>
