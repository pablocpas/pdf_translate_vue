<template>
  <div class="pdf-editor-container">
    <div v-if="isLoading" class="loading-overlay">Cargando Editor...</div>
    <div v-if="error" class="error-message">{{ error }}</div>

    <!-- Contenedor principal que permite posicionar los overlays sobre el PDF -->
    <div v-if="pdfSource" class="pdf-wrapper" ref="pdfWrapper">
      
      <!-- Visor de PDF -->
      <vue-pdf-embed 
        :source="pdfSource" 
        :page="currentPage" 
        @rendered="handlePageRendered"
      />

      <!-- Contenedor de overlays para la página actual -->
      <div class="overlay-container">
        <div
          v-for="overlay in pageOverlays"
          :key="overlay.id"
          class="text-region-overlay"
          :style="overlay.style"
          @click="openEditor(overlay.regionData)"
        >
          <!-- Opcional: Mostrar un pequeño ícono de edición -->
          <span class="edit-icon">✏️</span>
        </div>
      </div>
    </div>
    
    <div class="pagination" v-if="totalPages > 1">
        <button @click="prevPage" :disabled="currentPage <= 1">Anterior</button>
        <span>Página {{ currentPage }} de {{ totalPages }}</span>
        <button @click="nextPage" :disabled="currentPage >= totalPages">Siguiente</button>
    </div>

    <button @click="saveAllChanges" class="save-all-button" :disabled="isSaving">
      {{ isSaving ? 'Guardando...' : 'Guardar Todos los Cambios' }}
    </button>

    <!-- Modal de Edición -->
    <div v-if="editingRegion" class="modal-backdrop" @click.self="closeEditor">
      <div class="modal-content">
        <h3>Editar Traducción (Región #{{ editingRegion.id }})</h3>
        <div class="text-comparison">
          <h4>Texto Original</h4>
          <p>{{ getOriginalText(editingRegion.id) }}</p>
        </div>
        <textarea v-model="editingRegion.translated_text" rows="8"></textarea>
        <div class="modal-actions">
          <button @click="saveRegionEdit">Guardar</button>
          <button @click="closeEditor">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import VuePdfEmbed from 'vue-pdf-embed';
import axios from 'axios'; // o tu cliente http preferido

const props = defineProps({
  taskId: {
    type: String,
    required: true,
  },
});

// --- Estado (Refs y Reactives) ---
const isLoading = ref(true);
const isSaving = ref(false);
const error = ref(null);

const pdfSource = ref(null);
const translationData = ref({ pages: [] });
const positionData = ref({ pages: [] });

const pdfWrapper = ref(null); // Ref al contenedor del PDF
const pageDimensions = ref({}); // Almacena las dimensiones renderizadas de cada página { 1: { width, height }, ... }

const currentPage = ref(1);
const totalPages = computed(() => positionData.value?.pages?.length || 0);

const editingRegion = ref(null); // La región que se está editando actualmente

// --- Lógica de Datos ---

onMounted(async () => {
  await fetchData();
});

async function fetchData() {
  isLoading.value = true;
  error.value = null;
  try {
    const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    // Peticiones en paralelo para mayor eficiencia
    const [pdfRes, transRes, posRes] = await Promise.all([
      axios.get(`${VITE_API_URL}/pdfs/download/translated/${props.taskId}`),
      axios.get(`${VITE_API_URL}/pdfs/translation-data/${props.taskId}`),
      axios.get(`${VITE_API_URL}/pdfs/translated/${props.taskId}/position`),
    ]);

    pdfSource.value = transRes.data.url; // Asumimos que el backend devuelve una URL prefirmada
    translationData.value = transRes.data;
    positionData.value = posRes.data;
    
    // Corrección para asegurar que la URL sea válida para vue-pdf-embed
    // A veces es necesario un proxy si hay problemas de CORS con S3/MinIO
    pdfSource.value = pdfRes.data.url;


  } catch (err) {
    console.error("Error al cargar los datos de la traducción:", err);
    error.value = "No se pudieron cargar los datos para la edición. Por favor, inténtelo de nuevo.";
  } finally {
    isLoading.value = false;
  }
}

// --- Lógica del Visor de PDF y Overlays ---

// Se dispara cada vez que una página del PDF se renderiza en el DOM
function handlePageRendered(event) {
  // `event.page` es el objeto de la página de pdf.js
  // `event.source` es el elemento canvas/div renderizado
  const pageNumber = event.page.pageNumber;
  const viewport = event.page.getViewport({ scale: 1 }); // Viewport sin escalar (dimensiones en puntos)
  
  pageDimensions.value[pageNumber] = {
    // Dimensiones reales en píxeles en la pantalla
    renderedWidth: event.source.clientWidth,
    renderedHeight: event.source.clientHeight,
    // Dimensiones originales del PDF en puntos
    originalWidth: viewport.width,
    originalHeight: viewport.height,
    // Factor de escala para convertir puntos a píxeles de pantalla
    scaleFactor: event.source.clientWidth / viewport.width,
  };
}

// Propiedad computada que calcula los overlays para la página actual
const pageOverlays = computed(() => {
  if (!positionData.value.pages.length || !pageDimensions.value[currentPage.value]) {
    return [];
  }

  const currentPagePositions = positionData.value.pages.find(p => p.page_number === currentPage.value - 1);
  if (!currentPagePositions) return [];

  const dims = pageDimensions.value[currentPage.value];

  return currentPagePositions.regions.map(region => {
    // Los datos de posición vienen del backend en "puntos" (PDF units)
    // Necesitamos convertirlos a píxeles usando el factor de escala
    const pos = region.position;
    const style = {
      left: `${pos.x * dims.scaleFactor}px`,
      // La coordenada Y del PDF es desde abajo, en CSS es desde arriba.
      top: `${(dims.originalHeight - pos.y - pos.height) * dims.scaleFactor}px`,
      width: `${pos.width * dims.scaleFactor}px`,
      height: `${pos.height * dims.scaleFactor}px`,
    };
    return { id: region.id, style, regionData: region };
  });
});


// --- Lógica de Edición y Guardado ---

function getOriginalText(regionId) {
    const page = translationData.value.pages.find(p => p.page_number === currentPage.value - 1);
    const translation = page?.translations.find(t => t.id === regionId);
    return translation?.original_text || 'No disponible';
}


function openEditor(region) {
  const pageData = translationData.value.pages.find(p => p.page_number === currentPage.value - 1);
  const trans = pageData?.translations.find(t => t.id === region.id);
  if (trans) {
    // Clonamos el objeto para no modificar el estado directamente hasta guardar
    editingRegion.value = { ...trans };
  }
}

function saveRegionEdit() {
  if (!editingRegion.value) return;

  const pageIndex = translationData.value.pages.findIndex(p => p.page_number === currentPage.value - 1);
  if (pageIndex > -1) {
    const transIndex = translationData.value.pages[pageIndex].translations.findIndex(t => t.id === editingRegion.value.id);
    if (transIndex > -1) {
      // Actualizamos el estado principal con el texto modificado
      translationData.value.pages[pageIndex].translations[transIndex] = editingRegion.value;
    }
  }
  closeEditor();
}

function closeEditor() {
  editingRegion.value = null;
}

async function saveAllChanges() {
  isSaving.value = true;
  error.value = null;
  try {
    const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    await axios.put(
      `${VITE_API_URL}/pdfs/translation-data/${props.taskId}`,
      translationData.value
    );
    alert("¡Cambios guardados correctamente! El PDF se ha regenerado.");
    // Opcional: recargar los datos para obtener la nueva URL del PDF
    await fetchData();

  } catch (err) {
    console.error("Error al guardar los cambios:", err);
    error.value = "No se pudieron guardar los cambios.";
  } finally {
    isSaving.value = false;
  }
}

// --- Paginación ---
function prevPage() {
    if (currentPage.value > 1) currentPage.value--;
}

function nextPage() {
    if (currentPage.value < totalPages.value) currentPage.value++;
}

</script>

<style scoped>
.pdf-editor-container {
  max-width: 900px;
  margin: auto;
}

.pdf-wrapper {
  position: relative; /* Clave para el posicionamiento de los overlays */
  border: 1px solid #ccc;
  margin-bottom: 1rem;
}

.overlay-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Permite hacer clic "a través" del contenedor */
}

.text-region-overlay {
  position: absolute;
  border: 2px dashed rgba(255, 0, 0, 0.7);
  background-color: rgba(255, 0, 0, 0.1);
  cursor: pointer;
  pointer-events: auto; /* Habilita los clics solo en los overlays */
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.text-region-overlay:hover {
  background-color: rgba(255, 0, 0, 0.3);
}

.edit-icon {
    font-size: 1.5rem;
    opacity: 0;
    transition: opacity 0.2s;
}

.text-region-overlay:hover .edit-icon {
    opacity: 1;
}

.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
}

.save-all-button {
  display: block;
  width: 100%;
  padding: 1rem;
  font-size: 1.2rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  cursor: pointer;
}

.save-all-button:disabled {
  background-color: #aaa;
}

/* Estilos del Modal */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
}

.modal-content h3 {
    margin-top: 0;
}

.text-comparison {
    background-color: #f0f0f0;
    border-left: 4px solid #ccc;
    padding: 0.1rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9em;
}
.text-comparison p {
    color: #555;
}

.modal-content textarea {
  width: 100%;
  box-sizing: border-box;
  font-size: 1rem;
  padding: 0.5rem;
}

.modal-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}
</style>