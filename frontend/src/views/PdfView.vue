<template>
  <div class="pdf-viewer">
    <vue-pdf-app style="height: 100vh;" :pdf="pdfUrl" @error="handleError"></vue-pdf-app>

    <transition name="fade">
      <div v-if="error" class="error">{{ error }}</div>
    </transition>

    <transition name="fade">
      <button @click="summarizePdf" :disabled="loading || buttonPressed" class="summarize-button">
        {{ loading ? "Summarizing..." : "Summarize PDF" }}
      </button>
    </transition>

    <!-- Rendered Summary -->
    <transition name="slide-up">
      <div v-if="summary" class="summary-rendered" v-html="renderedSummary"></div>
    </transition>

    <!-- Chat Section -->
    <div class="chat-section">
      <div class="chat-history-rendered">
        <div v-for="(entry, index) in chatHistory" :key="index" class="chat-entry-rendered">
          <div class="user-question-rendered">
            <strong>Q:</strong> {{ entry.question }}
          </div>
          <div class="chat-response-rendered" v-html="renderMarkdown(entry.answer)"></div>
          <div v-if="entry.source" class="source-rendered">Source: {{ entry.source }}</div>
          <div v-if="entry.timestamp" class="timestamp-rendered">
            {{ new Date(entry.timestamp).toLocaleString() }}
          </div>
        </div>
      </div>

      <textarea
        v-model="userMessage"
        placeholder="Ask something about the document..."
        rows="4"
        class="chat-input"
      ></textarea>
      <button
        @click="sendMessage"
        :disabled="chatLoading || !userMessage.trim()"
        class="chat-button"
      >
        {{ chatLoading ? "Loading..." : "Send" }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import VuePdfApp from "vue3-pdf-app";
import { marked } from "marked";

export default {
  name: "PdfView",
  components: {
    VuePdfApp
  },
  props: {
    filePath: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const error = ref(null);
    const summary = ref(null);
    const userMessage = ref("");
    const chatHistory = ref([]);
    const loading = ref(false);
    const chatLoading = ref(false);
    const buttonPressed = ref(false);

    const pdfUrl = computed(() => `http://127.0.0.1:8000/file/${encodeURIComponent(props.filePath)}`);
    const renderedSummary = computed(() => marked(summary.value || ""));
    const renderMarkdown = (text) => marked(text || "");

    const handleError = (err) => {
      console.error("PDF loading error:", err);
      error.value = "Failed to load PDF. Please try again.";
    };

    const loadChatHistory = async () => {
      try {
        const filename = props.filePath.split("/").pop();
        const response = await fetch(`http://127.0.0.1:8000/chat-history/${encodeURIComponent(filename)}`);
        if (!response.ok) throw new Error("Failed to load chat history");
        const history = await response.json();
        chatHistory.value = history;
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    };

    const summarizePdf = async () => {
      loading.value = true;
      error.value = null;
      summary.value = null;
      buttonPressed.value = true;

      try {
        const response = await fetch(`http://127.0.0.1:8000/summarize/${encodeURIComponent(props.filePath)}`);
        if (!response.ok) throw new Error("Failed to summarize PDF.");

        pollSummary();
      } catch (err) {
        error.value = "Failed to summarize PDF. Please try again.";
        loading.value = false;
        buttonPressed.value = false;
      }
    };

    const pollSummary = async () => {
      const fileName = props.filePath.split("/").pop();
      try {
        const summaryResponse = await fetch(`http://127.0.0.1:8000/summary/${encodeURIComponent(fileName)}`);
        if (summaryResponse.ok) {
          const summaryData = await summaryResponse.json();
          if (summaryData.status === "completed") {
            summary.value = summaryData.summary;
            loading.value = false;
          } else {
            setTimeout(pollSummary, 2000);
          }
        }
      } catch (err) {
        error.value = "Failed to retrieve summary. Please try again later.";
        loading.value = false;
        buttonPressed.value = false;
      }
    };

    const sendMessage = async () => {
      chatLoading.value = true;
      error.value = null;

      try {
        const filename = props.filePath.split("/").pop();
        const response = await fetch("http://127.0.0.1:8000/chat-with-doc", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: userMessage.value,
            filename,
          }),
        });

        if (!response.ok) throw new Error("Failed to retrieve chat response.");

        const chatResult = await response.json();

        // Add the question and answer to the chat history
        chatHistory.value.push({
          question: userMessage.value,
          answer: chatResult.response,
          source: chatResult.source
        });
      } catch (err) {
        error.value = "Failed to send message. Please try again.";
      } finally {
        chatLoading.value = false;
        userMessage.value = "";
      }
    };

    onMounted(loadChatHistory);

    return {
      error,
      pdfUrl,
      handleError,
      summarizePdf,
      summary,
      loading,
      buttonPressed,
      renderedSummary,
      userMessage,
      sendMessage,
      chatHistory,
      chatLoading,
      renderMarkdown
    };
  },
};
</script>

<style scoped>
/* Keep your existing styles */
.chat {
  margin-top: 20px;
}

.chat-input {
  width: 100%;
  padding: 10px;
  border-radius: 5px;
  border: 1px solid #ccc;
  font-size: 1rem;
  margin-bottom: 10px;
  box-sizing: border-box;
}

.chat-button {
  display: block;
  padding: 10px 20px;
  font-size: 1.2rem;
  color: white;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  margin-top: 10px;
  transition: background-color 0.3s, transform 0.3s;
}

.chat-button:hover {
  background-color: #0056b3;
}

.chat-button:disabled {
  background-color: #b0c4de;
  cursor: not-allowed;
}

.chat-response {
  margin-top: 20px;
  background-color: #2e2e38;
  padding: 20px;
  border-radius: 10px;
  color: #e6e6e6;
}

.chat-response .source {
  font-size: 0.9rem;
  color: #b0b0b0;
  margin-top: 10px;
}


.chat-history {
  margin-top: 20px;
  padding: 20px;
  background-color: #2e2e38;
  border-radius: 10px;
  color: #e6e6e6;
}

.chat-entry {
  margin-bottom: 20px;
}

.user-question {
  font-size: 1.1rem;
  font-weight: bold;
  margin-bottom: 10px;
}

.chat-response {
  margin-left: 10px;
}

.chat-response .source {
  font-size: 0.9rem;
  color: #b0b0b0;
  margin-top: 10px;
}
.pdf-viewer {
  position: relative;
  height: 100vh;
  padding: 20px;
  background-color: #1e1e2f; /* Dark background */
  font-family: 'Arial', sans-serif;
  color: #e6e6e6; /* Light text for contrast */
}

.summary-rendered {
  margin-top: 20px;
  padding: 20px;
  background-color: black; /* Black background for summary */
  border-radius: 10px;
  color: #e6e6e6; /* Light text for contrast */
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  overflow-y: auto;
}

.chat-section {
  margin-top: 20px;
  padding: 20px;
  background-color: #2e2e38;
  border-radius: 10px;
}

.chat-history-rendered {
  max-height: 600px;
  overflow-y: auto;
  padding: 10px;
  background-color: #1e1e2f;
  border-radius: 10px;
  margin-bottom: 20px;
}

.chat-entry-rendered {
  margin-bottom: 20px;
}

.user-question-rendered {
  font-size: 1.1rem;
  font-weight: bold;
  margin-bottom: 10px;
}

.chat-response-rendered {
  margin-left: 10px;
  font-size: 1rem;
}

.source-rendered {
  font-size: 0.9rem;
  color: #b0b0b0;
  margin-top: 5px;
}

.chat-response-rendered {
  margin-left: 10px;
  font-size: 1rem;
  background-color: #2e2e38; /* Slightly darker background */
  padding: 10px;
  border-radius: 5px;
  color: #e6e6e6;
  line-height: 1.5;
}

.chat-response-rendered ul,
.chat-response-rendered ol {
  margin-left: 20px;
  padding-left: 20px;
}

.chat-response-rendered code {
  background-color: #3e3e48;
  color: #ffcc99;
  padding: 2px 4px;
  border-radius: 4px;
}

.timestamp-rendered {
  font-size: 0.8rem;
  color: #666;
  text-align: right;
  margin-top: 5px;
}

</style>
