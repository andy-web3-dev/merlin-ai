import markdownit from 'markdown-it'
import highlightjs from 'markdown-it-highlightjs'
import { Component, computed, defineComponent, h, ref } from 'vue'

const Markdown: Component = defineComponent({
  props: {
    source: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const md = ref<markdownit>(
      markdownit({
        html: true, // Enable HTML tags support
      }),
    )

    md.value.use(highlightjs, {
      inline: true,
      auto: true,
      ignoreIllegals: true,
    })

    // Add custom iframe handling
    md.value.use((md) => {
      const defaultRender =
        md.renderer.rules.html_block ||
        function (tokens, idx, options, env, self) {
          return self.renderToken(tokens, idx, options)
        }

      md.renderer.rules.html_block = function (tokens, idx, options, env, self) {
        const token = tokens[idx]

        // Check for iframe tags
        if (token.content.includes('<iframe')) {
          // For security, you might want to validate the iframe src
          // and only allow specific domains
          return token.content.replace(
            /<iframe(.*?)>(.*?)<\/iframe>/g,
            (match, attributes) => {
              // Add additional security attributes
              return `<iframe${attributes}
                    sandbox="allow-scripts allow-same-origin"
                    loading="lazy"
                    width="600px"
                    height="500px"
                    class="markdown-iframe">${match}</iframe>`
            },
          )
        }
        return defaultRender(tokens, idx, options, env, self)
      }
    })

    const content = computed(() => md.value.render(props.source))

    return () => h('div', { innerHTML: content.value })
  },
})

export default Markdown
