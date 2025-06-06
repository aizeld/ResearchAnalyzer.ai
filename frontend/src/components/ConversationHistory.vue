<template>
  <div class="conversation-history">
    <h3>Conversation History</h3>
    <div v-if="loading" class="loading">
      Loading conversation history...
    </div>
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    <div v-else-if="conversations.length === 0" class="no-history">
      No conversation history for this file yet.
    </div>
    <div v-else class="conversation-list">
      <div v-for="conv in conversations" :key="conv.id" class="conversation-entry">
        <div class="question">
          <strong>Q:</strong> {{ conv.question }}
        </div>
        <div class="answer">
          <strong>A:</strong> {{ conv.answer }}
        </div>
        <div class="timestamp">
          {{ new Date(conv.timestamp).toLocaleString() }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConversationHistory',
  props: {
    fileId: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      conversations: [],
      loading: true,
      error: null
    }
  },
  watch: {
    fileId: {
      immediate: true,
      handler: 'loadConversations'
    }
  },
  methods: {
    async loadConversations() {
      if (!this.fileId) return;
      
      this.loading = true;
      this.error = null;
      
      try {
        const response = await fetch(`http://localhost:8000/conversation/history/${this.fileId}`);
        if (!response.ok) {
          throw new Error('Failed to load conversation history');
        }
        this.conversations = await response.json();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    }
  }
}
</script>

<style scoped>
.conversation-history {
  padding: 1rem;
  max-height: 500px;
  overflow-y: auto;
}

.conversation-entry {
  margin-bottom: 1.5rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #f9f9f9;
}

.question, .answer {
  margin-bottom: 0.5rem;
}

.timestamp {
  font-size: 0.8rem;
  color: #666;
  text-align: right;
}

.loading, .error, .no-history {
  text-align: center;
  padding: 1rem;
  color: #666;
}

.error {
  color: #dc3545;
}
</style> 