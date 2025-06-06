<template>
  <div class="settings-menu">
    <button class="settings-button" @click.stop="toggleMenu">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="1"></circle>
        <circle cx="12" cy="5" r="1"></circle>
        <circle cx="12" cy="19" r="1"></circle>
      </svg>
    </button>

    <div v-if="isMenuOpen" class="menu-dropdown">
      <div class="menu-item" @click.stop="startRename">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 20h9"></path>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
        </svg>
        Rename
      </div>
      <div class="menu-item delete" @click.stop="startDelete">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 6h18"></path>
          <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
          <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
        </svg>
        Delete
      </div>
    </div>

    <!-- Confirmation Dialog -->
    <div v-if="showConfirmation" class="confirmation-overlay">
      <div class="confirmation-modal">
        <h3>Delete File</h3>
        <p>Are you sure you want to delete "{{ filename }}"?</p>
        <div class="confirmation-buttons">
          <button @click="cancelDelete">Cancel</button>
          <button class="delete-button" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </div>

    <!-- Rename Dialog -->
    <div v-if="showRename" class="modal-overlay">
      <div class="modal">
        <h3>Rename File</h3>
        <input 
          type="text" 
          v-model="newFileName" 
          placeholder="Enter new file name"
          @keyup.enter="renameFile"
          ref="renameInput"
        >
        <div class="modal-buttons">
          <button @click="cancelRename">Cancel</button>
          <button @click="renameFile" :disabled="!newFileName">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';

export default {
  name: 'FileSettingsMenu',
  props: {
    filename: {
      type: String,
      required: true
    }
  },
  setup() {
    const isMenuOpen = ref(false);
    const showRename = ref(false);
    const showConfirmation = ref(false);
    const newFileName = ref('');
    const renameInput = ref(null);

    const closeMenu = (e) => {
      if (!e.target.closest('.settings-menu')) {
        isMenuOpen.value = false;
        showConfirmation.value = false;
      }
    };

    onMounted(() => {
      document.addEventListener('click', closeMenu);
    });

    onUnmounted(() => {
      document.removeEventListener('click', closeMenu);
    });

    return {
      isMenuOpen,
      showRename,
      showConfirmation,
      newFileName,
      renameInput
    };
  },
  methods: {
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
      if (!this.isMenuOpen) {
        this.showConfirmation = false;
      }
    },
    startDelete() {
      this.isMenuOpen = false;
      this.showConfirmation = true;
    },
    startRename() {
      this.newFileName = this.filename;
      this.showRename = true;
      this.isMenuOpen = false;
      this.$nextTick(() => {
        if (this.$refs.renameInput) {
          this.$refs.renameInput.focus();
          this.$refs.renameInput.select();
        }
      });
    },
    async confirmDelete() {
      try {
        const response = await fetch(`http://127.0.0.1:8000/delete_ingested/${encodeURIComponent(this.filename)}`, {
          method: 'DELETE',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to delete file');
        }

        const result = await response.json();
        console.log('Delete successful:', result);
        this.$emit('file-deleted');
        this.showConfirmation = false;
      } catch (error) {
        console.error('Error deleting file:', error);
        alert(`Failed to delete file: ${error.message}`);
      }
    },
    cancelDelete() {
      this.showConfirmation = false;
    },
    async renameFile() {
      if (this.newFileName && this.newFileName !== this.filename) {
        try {
          const response = await fetch(`http://127.0.0.1:8000/rename-file/${encodeURIComponent(this.filename)}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_filename: this.newFileName })
          });

          if (!response.ok) throw new Error('Failed to rename file');

          this.$emit('file-renamed', this.newFileName);
          this.showRename = false;
        } catch (error) {
          console.error('Error renaming file:', error);
          alert('Failed to rename file. Please try again.');
        }
      }
    },
    cancelRename() {
      this.showRename = false;
      this.newFileName = '';
    }
  }
};
</script>

<style scoped>
.settings-menu {
  position: relative;
  display: inline-block;
  z-index: 100;
}

.settings-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px;
  color: #666;
  transition: color 0.3s;
  opacity: 0;
  margin-left: 8px;
}

.file-item:hover .settings-button {
  opacity: 1;
}

.settings-button:hover {
  color: #333;
}

.menu-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  min-width: 150px;
}

.menu-item {
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
  color: #333;
}

.menu-item:hover {
  background-color: #f5f5f5;
}

.menu-item.delete {
  color: #dc3545;
}

.menu-item.delete:hover {
  background-color: #ffebee;
}

.confirmation-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.confirmation-modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  min-width: 300px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.confirmation-modal h3 {
  margin: 0 0 16px 0;
  color: #333;
}

.confirmation-modal p {
  margin: 0 0 20px 0;
  color: #666;
}

.confirmation-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.confirmation-buttons button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.confirmation-buttons button:first-child {
  background-color: #e0e0e0;
}

.confirmation-buttons button:first-child:hover {
  background-color: #d0d0d0;
}

.confirmation-buttons .delete-button {
  background-color: #dc3545;
  color: white;
}

.confirmation-buttons .delete-button:hover {
  background-color: #c82333;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  min-width: 300px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.modal h3 {
  margin: 0 0 16px 0;
  color: #333;
}

.modal input {
  width: 100%;
  padding: 8px;
  margin-bottom: 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.modal input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.modal-buttons button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.modal-buttons button:first-child {
  background-color: #e0e0e0;
}

.modal-buttons button:first-child:hover {
  background-color: #d0d0d0;
}

.modal-buttons button:last-child {
  background-color: #007bff;
  color: white;
}

.modal-buttons button:last-child:hover {
  background-color: #0056b3;
}

.modal-buttons button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style> 