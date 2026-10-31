<script setup>
/** The foot of every page, as After the Poem's: who made it, the version, where
 * the schema and the source are, and the licences. Plain words, no labels. */
import { useData, withBase } from 'vitepress';

const { theme } = useData();
</script>

<template>
  <footer class="gf-footer">
    <span>© 2026 Mirza Husadzic</span>
    <span>Gadfly {{ theme.gadfly.version }}</span>
    <a :href="withBase('/frame.schema.json')">Frame schema</a>
    <a :href="theme.gadfly.github">Source on GitHub</a>
    <a :href="`${theme.gadfly.github}/blob/main/LICENSE`">Code under Apache 2.0</a>
    <a :href="`${theme.gadfly.github}/blob/main/LICENSES/CC-BY-4.0.txt`">The essay under CC BY 4.0</a>
    <a :href="withBase('/notices')">Fonts and libraries</a>
    <a href="https://vitepress.dev">Built with VitePress</a>
  </footer>
</template>
