<script setup>
/** The gadfly before the site's name in the top bar: docs/public/gadfly.svg,
 * drawn inline so it takes the study's title colour. */
import drawing from '../../public/gadfly.svg?raw';
</script>

<template>
  <span class="gf-mark" aria-hidden="true" v-html="drawing" />
</template>
