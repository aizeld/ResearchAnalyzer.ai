<script setup>
import { ref, onMounted } from "vue";
const paperLink = ref("");
const doi = ref("");
const message = ref(null);
const filePath = ref(null);
const error = ref(null);
const file = ref(null);
const mounted = ref(false);

const extractDOI = (link) => {
  const doiMatch = link.match(/10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i);
  return doiMatch ? doiMatch[0] : null;
};

const onFileChange = (event) => {
  file.value = event.target.files[0];
  paperLink.value = ""; // Clear DOI input if a file is selected
  error.value = null;
};

const submitDOI = async () => {
  error.value = null;
  message.value = null;
  doi.value = null;

  if (!paperLink.value) {
    error.value = "Please provide a DOI";
    return;
  }

  const extractedDOI = extractDOI(paperLink.value);
  if (!extractedDOI) {
    error.value = "Invalid link or DOI not found.";
    return;
  }

  doi.value = extractedDOI;

  try {
    const response = await fetch("http://127.0.0.1:8000/process-doi", {
      method: "POST",
      body: JSON.stringify(
        {
          "doi": doi.value,
        }
      ),
      headers: {
        "Content-Type": "application/json",
      }
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "Error processing the request.");
    }

    if (result.file_path) {
      filePath.value = result.file_path;
    }

    message.value = result.message || "Success!";
  } catch (err) {
    error.value = `Error: ${err.message}`;
  }
};

const submitFile = async () => {
  error.value = null;
  message.value = null;
  filePath.value = null;

  const formData = new FormData();

  if (!file.value) {
    error.value = "Please provide a PDF file.";
    return;
  }

  if (file.value.type !== "application/pdf") {
    error.value = "The uploaded file must be a PDF.";
    return;
  }
  formData.append('file', file.value)

  try {
    const response = await fetch("http://127.0.0.1:8000/process-pdf", {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "Error processing the request.");
    }

    if (result.file_path) {
      filePath.value = result.file_path;
    }

    message.value = result.message || "Success!";
  } catch (err) {
    error.value = `Error: ${err.message}`;
  }
};

onMounted(() => {
  mounted.value = true;
});

</script>

<template>
  <transition name="slide-from-top">
    <div class="paper-download" v-if="mounted">
      <!-- File upload form-->
      <form @submit.prevent="submitFile" class="form-container">
        <!-- File upload for PDFs -->
        <label for="file-upload">Upload a PDF file:</label>
        <input type="file" id="file-upload" @change="onFileChange" accept="application/pdf" />

        <!-- Submit button -->
        <button type="submit" class="submit-button">Submit</button>
      </form>

      <!-- DOI upload form -->
      <form @submit.prevent="submitDOI" class="form-container">
        <!-- Input for paper link -->
        <label for="paper-link">Enter paper link (optional):</label>
        <input type="text" v-model="paperLink" id="paper-link" placeholder="https://doi.org/something..."
          :disabled="file" />

        <!-- Submit button -->
        <button type="submit" class="submit-button">Submit</button>
      </form>



      <!-- Feedback messages with transitions -->
      <transition name="fade">
        <p v-if="doi" class="info">Extracted DOI: {{ doi }}</p>
      </transition>
      <transition name="fade">
        <p v-if="message" class="info success">Message: {{ message }}</p>
      </transition>
      <transition name="fade">
        <p v-if="filePath" class="info">File Path: {{ filePath }}</p>
      </transition>
      <transition name="fade">
        <p v-if="error" class="info error">{{ error }}</p>
      </transition>
    </div>
  </transition>
</template>
<style scoped>
/* Reuse the same styles from the provided design */
.paper-download {
  max-width: 400px;
  margin: auto;
  padding: 20px;
  background: #f7f9fc;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-size: 1rem;
  transition: border-color 0.3s, box-shadow 0.3s;
}

input:focus {
  border-color: #007bff;
  box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
  outline: none;
}

.submit-button {
  padding: 10px;
  font-size: 1rem;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s, transform 0.3s;
}

.submit-button:hover {
  background-color: #0056b3;
}

.submit-button:active {
  transform: scale(0.95);
}

.info {
  margin-top: 10px;
  padding: 10px;
  border-radius: 5px;
  font-size: 1rem;
  transition: opacity 0.3s;
}

.success {
  background-color: #d4edda;
  color: #155724;
}

.error {
  background-color: #f8d7da;
  color: #721c24;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter,
.fade-leave-to {
  opacity: 0;
}

.slide-from-top-enter-active {
  transition: transform 0.5s ease, opacity 0.5s ease;
}

.slide-from-top-enter {
  transform: translateY(-50px);
  opacity: 0;
}

.slide-from-top-leave-active {
  transition: transform 0.5s ease, opacity 0.5s ease;
}

.slide-from-top-leave-to {
  transform: translateY(-50px);
  opacity: 0;
}
</style>
