<template>
  <div class="file-manager">
    <h2>Uploaded Files</h2>
    <transition-group name="slide-fade" tag="ul" class="file-list">
      <li v-for="file in files" :key="file.name" class="file-item">
        <div class="file-content">
          <!-- Normal View -->
          <div v-if="!file.isEditing" class="file-name" @dblclick="startEditing(file)">
            {{ file.name }}
          </div>
          <!-- Edit View -->
          <div v-else class="file-name-edit">
            <input
              type="text"
              v-model="file.editName"
              ref="fileNameInput"
              @keyup.enter="saveFileName(file)"
              @keyup.esc="cancelEditing(file)"
              @blur="cancelEditing(file)"
            >
          </div>
          <FileSettingsMenu 
            :filename="file.name"
            @file-deleted="handleFileDeleted"
            @file-renamed="handleFileRenamed(file.name, $event)"
          />
        </div>
        <div class="file-actions">
          <router-link
            :to="`/files/${encodeURIComponent(file.name)}`"
            target="_blank"
            class="view-button"
          >
            View
          </router-link>
        </div>
      </li>
    </transition-group>
    <transition name="fade">
      <p v-if="files.length === 0">No files uploaded yet.</p>
    </transition>
    <transition name="fade">
      <p v-if="error" class="error">{{ error }}</p>
    </transition>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import FileSettingsMenu from '../components/FileSettingsMenu.vue';

export default {
  components: {
    FileSettingsMenu
  },
  setup() {
    const files = ref([]);
    const error = ref(null);
    const fileNameInput = ref(null);

    const fetchFiles = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/files');
        const result = await response.json();
        if (result.status_code !== 200) {
          throw new Error(result.detail || 'Error fetching files');
        }
        // Add isEditing and editName properties to each file
        files.value = result.files.map(file => ({
          ...file,
          isEditing: false,
          editName: file.name
        }));
      } catch (err) {
        error.value = `Error: ${err.message}`;
      }
    };

    const startEditing = (file) => {
      // Cancel any other file being edited
      files.value.forEach(f => {
        if (f !== file) {
          f.isEditing = false;
          f.editName = f.name;
        }
      });
      
      file.isEditing = true;
      file.editName = file.name;
      // Focus the input on next tick after it's rendered
      setTimeout(() => {
        const input = document.querySelector('.file-name-edit input');
        if (input) {
          input.focus();
          // Select filename without extension
          const lastDotIndex = file.name.lastIndexOf('.');
          if (lastDotIndex > 0) {
            input.setSelectionRange(0, lastDotIndex);
          } else {
            input.select();
          }
        }
      }, 0);
    };

    const saveFileName = async (file) => {
      if (!file.editName || file.editName === file.name) {
        cancelEditing(file);
        return;
      }

      try {
        const response = await fetch(`http://127.0.0.1:8000/rename-file/${encodeURIComponent(file.name)}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ new_filename: file.editName })
        });

        if (!response.ok) {
          throw new Error('Failed to rename file');
        }

        const result = await response.json();
        file.name = result.new_name;
        file.isEditing = false;
        await fetchFiles(); // Refresh the list
      } catch (err) {
        error.value = `Failed to rename file: ${err.message}`;
        cancelEditing(file);
      }
    };

    const cancelEditing = (file) => {
      file.isEditing = false;
      file.editName = file.name;
    };

    const handleFileDeleted = () => {
      fetchFiles(); // Refresh the file list
    };

    const handleFileRenamed = async (oldName, newName) => {
      await fetchFiles(); // Refresh the file list
    };

    onMounted(() => {
      fetchFiles();
    });

    return {
      files,
      error,
      fileNameInput,
      startEditing,
      saveFileName,
      cancelEditing,
      handleFileDeleted,
      handleFileRenamed
    };
  },
};
</script>

<style scoped>
.file-manager {
  position: fixed;
  top: 10%;
  left: 2%;
  max-width: 350px;
  padding: 20px;
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  font-family: 'Arial', sans-serif;
  overflow-y: auto;
  max-height: 80%;
  text-align: center;
  animation: slide-in-left 0.5s ease-in-out;
}

h2 {
  color: #333;
  font-size: 1.8rem;
  margin-bottom: 20px;
  text-align: center;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.file-item {
  margin: 10px 0;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 8px;
  transition: background-color 0.3s ease;
}

.file-item:hover {
  background-color: #e8f0fe;
}

.file-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.file-name {
  flex-grow: 1;
  font-size: 1rem;
  font-weight: 500;
  color: #333;
  cursor: text;
  padding: 4px 8px;
  border-radius: 4px;
  margin-right: 10px;
}

.file-name:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.file-name-edit {
  flex-grow: 1;
  margin-right: 10px;
}

.file-name-edit input {
  width: 100%;
  padding: 4px 8px;
  font-size: 1rem;
  font-weight: 500;
  border: 1px solid #007bff;
  border-radius: 4px;
  outline: none;
  background: white;
}

.file-actions {
  display: flex;
  justify-content: flex-end;
}

.view-button {
  text-decoration: none;
  padding: 4px 12px;
  font-size: 0.9rem;
  color: #007bff;
  background-color: transparent;
  border: 1px solid #007bff;
  border-radius: 4px;
  transition: all 0.2s;
}

.view-button:hover {
  background-color: #007bff;
  color: white;
}

.error {
  color: red;
  font-size: 1.1rem;
  margin-top: 10px;
}

@keyframes slide-in-left {
  from {
    opacity: 0;
    transform: translateX(-100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter, .fade-leave-to {
  opacity: 0;
}

.slide-fade-enter-active {
  transition: all 0.5s ease;
}

.slide-fade-enter, .slide-fade-leave-to {
  transform: translateX(-10px);
  opacity: 0;
}

@media (max-width: 768px) {
  .file-manager {
    left: 5%;
    max-width: 80%;
    padding: 15px;
  }

  h2 {
    font-size: 1.5rem;
  }

  .file-link {
    font-size: 0.9rem;
  }
}
</style>
