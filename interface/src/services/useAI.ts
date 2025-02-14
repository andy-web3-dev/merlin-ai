import {
  ChatCompletedResponse,
  ChatPartResponse,
  ChatResponse,
  Model,
  useApi,
} from './api.ts'

import { ref } from 'vue'
import { Message } from './database'

// Define availableModels outside the function to ensure a shared state.
const availableModels = ref<Model[]>([])

export const useAI = () => {
  const { generateChat, listLocalModels } = useApi()
  const generate = async (
    model: string,
    messages: Message[],
    system?: Message,
    historyMessageLength?: number,
    onMessage?: (
      data: ChatResponse | ChatPartResponse | ChatCompletedResponse,
    ) => Promise<void>,
    onDone?: (data: ChatCompletedResponse) => Promise<void>,
  ) => {
    let chatHistory = messages.slice(-(historyMessageLength ?? 0))
    if (system) {
      chatHistory.unshift(system)
    }
    await generateChat({ model, messages: chatHistory }, async (data: ChatResponse) => {
      if (!data.done && onMessage) {
        await onMessage(data as ChatPartResponse)
      } else if (data.done && onDone) {
        await onDone(data as ChatCompletedResponse)
      }
    })
  }

  const refreshModels = async () => {
    const response = await listLocalModels()
    availableModels.value = response.models
  }

  // Use toRefs to keep reactivity when destructuring in components.
  return {
    availableModels,
    generate,
    refreshModels,
  }
}
