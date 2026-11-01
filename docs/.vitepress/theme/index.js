// VitePress's default theme in Gadfly's faces and colours (custom.css), with
// the gadfly before the site's name (GadflyMark.vue), the colour menu
// (ThemeMenu.vue), the charts (MermaidDiagram.vue), the foot of every page
// (SiteFooter.vue) and the watch view.
import { useRoute, withBase } from 'vitepress';
import DefaultTheme from 'vitepress/theme-without-fonts';
import { h, nextTick, onMounted, watch } from 'vue';
import GadflyMark from './GadflyMark.vue';
import MermaidDiagram from './MermaidDiagram.vue';
import SiteFooter from './SiteFooter.vue';
import ThemeMenu from './ThemeMenu.vue';
import './custom.css';
import './watch.css';

export default {
  extends: DefaultTheme,
  // The theme menu takes the place of VitePress's light and dark switch: in
  // the top bar, and as a list in the phone's menu screen.
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      'nav-bar-title-before': () => h(GadflyMark),
      'nav-bar-content-after': () => h(ThemeMenu),
      'nav-screen-content-after': () => h(ThemeMenu, { inline: true }),
      'doc-after': () => h(SiteFooter),
    }),
  enhanceApp({ app }) {
    app.component('MermaidDiagram', MermaidDiagram);
  },
  setup() {
    // The watch view (docs/public/javascripts/watch.js) builds itself into
    // each .gadfly-watch and .gadfly-compare on the page when it runs. Pages change here without
    // a page load, so it runs again each time a page with one is shown.
    const route = useRoute();
    const mount = () =>
      nextTick(() => {
        if (!document.querySelector('.gadfly-watch, .gadfly-compare')) return;
        const script = document.createElement('script');
        script.src = withBase('/javascripts/watch.js');
        script.onload = () => script.remove();
        document.body.append(script);
      });
    onMounted(mount);
    watch(() => route.path, mount);
  },
};
