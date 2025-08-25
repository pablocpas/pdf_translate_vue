<template>
  <div class="pdf-editor-container">
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
      <p>Cargando datos del editor...</p>
    </div>
    <div v-if="error" class="error-message">{{ error }}</div>

    <!-- Contenedor principal que permite posicionar los overlays sobre el PDF -->
    <div v-if="pdfSource" class="pdf-wrapper" ref="pdfWrapper">
      
      <!-- Visor de PDF con la librería vue-pdf-embed -->
      <vue-pdf-embed 
        :source="pdfSource" 
        :page="currentPage" 
        @rendered="handlePageRendered"
      />

      <!-- Contenedor de overlays que se superpone al PDF -->
      <div class="overlay-container">
        <!-- Generamos un div por cada región de texto detectada en la página actual -->
        <div
          v-for="overlay in pageOverlays"
          :key="overlay.id"
          class="text-region-overlay"
          :style="overlay.style"
          @click="openEditor(overlay.regionData)"
        >
          <!-- Ícono de edición que aparece al pasar el ratón -->
          <span class="edit-icon">✏️</span>
        </div>
      </div>
    </div>
    
    <div class="controls-bar" v-if="pdfSource">
      <button @click="saveAllChanges" class="save-all-button" :disabled="isSaving || isLoading">
        {{ isSaving ? 'Guardando...' : 'Guardar Todos los Cambios' }}
      </button>
      <div class="pagination" v-if="totalPages > 1">
          <button @click="prevPage" :disabled="currentPage <= 1">Anterior</button>
          <span>Página {{ currentPage }} de {{ totalPages }}</span>
          <button @click="nextPage" :disabled="currentPage >= totalPages">Siguiente</button>
      </div>
    </div>


    <!-- Modal de Edición: aparece cuando 'editingRegion' tiene datos -->
    <div v-if="editingRegion" class="modal-backdrop" @click.self="closeEditor">
      <div class="modal-content">
        <h3>Editar Traducción (Región #{{ editingRegion.id }})</h3>
        
        <div class="text-comparison">
          <h4>Texto Original (solo lectura)</h4>
          <p>{{ getOriginalText(editingRegion.id) }}</p>
        </div>
        
        <h4>Texto Traducido (editable)</h4>
        <textarea v-model="editingRegion.translated_text" rows="8" placeholder="Escribe aquí la nueva traducción"></textarea>
        
        <div class="modal-actions">
          <button @click="closeEditor" class="btn-cancel">Cancelar</button>
          <button @click="saveRegionEdit" class="btn-save">Guardar Región</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import VuePdfEmbed from 'vue-pdf-embed';
import axios from 'axios';

// El componente recibe el ID de la tarea como una propiedad (prop)
const props = defineProps({
  taskId: {
    type: String,
    required: true,
  },
});

// --- Estado Reactivo del Componente ---
const isLoading = ref(true);
const isSaving = ref(false);
const error = ref(null);

const pdfSource = ref(null); // URL del PDF a mostrar
const translationData = ref({ pages: [] }); // { pages: [ { page_number, translations: [ { id, original_text, translated_text } ] } ] }
const positionData = ref({ pages: [] });    // { pages: [ { page_number, dimensions, regions: [ { id, position: { x,y,w,h } } ] } ] }

const pdfWrapper = ref(null); // Referencia al div que contiene el visor de PDF
const pageDimensions = ref({}); // Almacena las dimensiones renderizadas de cada página: { 1: { width, height, scaleFactor }, ... }

const currentPage = ref(1);
const totalPages = computed(() => positionData.value?.pages?.length || 0);

const editingRegion = ref(null); // Almacena la región que se está editando en el modal. Si es null, el modal está cerrado.

// --- Lógica de Carga de Datos ---

// onMounted se ejecuta automáticamente cuando el componente se crea
onMounted(async () => {
  await fetchData();
});

async function fetchData() {
  isLoading.value = true;
  error.value = null;
  try {
    const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    // Hacemos las 2 peticiones de datos en paralelo (la URL del PDF la construimos directamente)
    const [transRes, posRes] = await Promise.all([
      axios.get(`${VITE_API_URL}/pdfs/translation-data/${props.taskId}`),   // Textos
      axios.get(`${VITE_API_URL}/pdfs/translated/${props.taskId}/position`),    // Coordenadas
    ]);
    
    // Asignamos los datos recibidos a nuestro estado reactivo
    pdfSource.value = `${VITE_API_URL}/pdfs/download/translated/${props.taskId}`;
    translationData.value = transRes.data;
    positionData.value = posRes.data;
    
    // Debug logging
    console.log('PDF Source:', pdfSource.value);
    console.log('Translation Data:', translationData.value);
    console.log('Position Data:', positionData.value);
    console.log('Total pages from position data:', positionData.value?.pages?.length);

  } catch (err) {
    console.error("Error al cargar los datos de la traducción:", err);
    error.value = "No se pudieron cargar los datos para la edición. Por favor, recarga la página.";
  } finally {
    isLoading.value = false;
  }
}

// --- Lógica del Visor de PDF y Overlays (la parte más importante) ---

// Esta función es llamada por vue-pdf-embed cada vez que una página se renderiza en pantalla
function handlePageRendered(event) {
  console.log('PDF page rendered event:', event);
  const pageNumber = event.page.pageNumber;
  // Obtenemos el viewport original del PDF (dimensiones en 'puntos', la unidad de medida de los PDF)
  const viewport = event.page.getViewport({ scale: 1 });
  
  // Guardamos las dimensiones clave para nuestros cálculos
  pageDimensions.value[pageNumber] = {
    // Dimensiones reales en píxeles que ocupa el PDF en la pantalla
    renderedWidth: event.source.clientWidth,
    renderedHeight: event.source.clientHeight,
    // Dimensiones originales del PDF en puntos
    originalWidth: viewport.width,
    originalHeight: viewport.height,
    // El factor de escala para convertir puntos a píxeles de pantalla
    scaleFactor: event.source.clientWidth / viewport.width,
  };
  
  console.log(`Page ${pageNumber} dimensions:`, pageDimensions.value[pageNumber]);
}

// Propiedad computada: recalcula los overlays cada vez que cambia la página actual o las dimensiones
const pageOverlays = computed(() => {
  console.log('Computing pageOverlays...');
  console.log('positionData.value:', positionData.value);
  console.log('positionData.value.pages.length:', positionData.value.pages?.length);
  console.log('currentPage.value:', currentPage.value);
  console.log('pageDimensions.value:', pageDimensions.value);
  
  // Si no tenemos los datos necesarios, devolvemos un array vacío
  if (!positionData.value.pages?.length || !pageDimensions.value[currentPage.value]) {
    console.log('Returning empty array - missing data');
    return [];
  }

  // Buscamos los datos de posición para la página actual (OJO: la paginación es 1-based, los datos 0-based)
  const currentPagePositions = positionData.value.pages.find(p => p.page_number === currentPage.value - 1);
  console.log('currentPagePositions:', currentPagePositions);
  if (!currentPagePositions) {
    console.log('No positions found for current page');
    return [];
  }

  const dims = pageDimensions.value[currentPage.value];
  console.log('Page dimensions:', dims);

  const overlays = currentPagePositions.regions.map(region => {
    const pos = region.position;
    
    // **AQUÍ ESTÁ LA MAGIA:** Convertimos las coordenadas de "puntos" del backend a píxeles de CSS
    const style = {
      // 'left' y 'width' son directos, solo se multiplican por el factor de escala
      left: `${pos.x * dims.scaleFactor}px`,
      width: `${pos.width * dims.scaleFactor}px`,
      
      // 'top' y 'height' necesitan un cálculo especial porque el eje Y está invertido
      // PDF (0,0) es abajo-izquierda. CSS (0,0) es arriba-izquierda.
      top: `${(dims.originalHeight - pos.y - pos.height) * dims.scaleFactor}px`,
      height: `${pos.height * dims.scaleFactor}px`,
    };
    return { id: region.id, style, regionData: region };
  });
  
  console.log('Generated overlays:', overlays);
  return overlays;
});


// --- Lógica de Edición y Guardado ---

function getOriginalText(regionId) {
    const page = translationData.value.pages.find(p => p.page_number === currentPage.value - 1);
    const translation = page?.translations.find(t => t.id === regionId);
    return translation?.original_text || 'Texto original no encontrado.';
}

function openEditor(region) {
  const pageData = translationData.value.pages.find(p => p.page_number === currentPage.value - 1);
  const trans = pageData?.translations.find(t => t.id === region.id);
  if (trans) {
    // Clonamos el objeto con {...} para no modificar el estado original hasta que se pulse "Guardar"
    editingRegion.value = { ...trans };
  }
}

function saveRegionEdit() {
  if (!editingRegion.value) return;

  const pageIndex = translationData.value.pages.findIndex(p => p.page_number === currentPage.value - 1);
  if (pageIndex > -1) {
    const transIndex = translationData.value.pages[pageIndex].translations.findIndex(t => t.id === editingRegion.value.id);
    if (transIndex > -1) {
      // Aquí SÍ actualizamos el estado principal con el texto modificado
      translationData.value.pages[pageIndex].translations[transIndex] = editingRegion.value;
    }
  }
  closeEditor(); // Cerramos el modal
}

function closeEditor() {
  editingRegion.value = null;
}

async function saveAllChanges() {
  isSaving.value = true;
  error.value = null;
  try {
    const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    // Enviamos el objeto 'translationData' completo y modificado al backend
    await axios.put(
      `${VITE_API_URL}/pdfs/translation-data/${props.taskId}`,
      translationData.value
    );
    alert("¡Cambios guardados correctamente! El PDF se ha regenerado.");
    // Volvemos a cargar los datos para obtener la URL del nuevo PDF y refrescar la vista
    await fetchData();

  } catch (err) {
    console.error("Error al guardar los cambios:", err);
    error.value = "No se pudieron guardar los cambios. Inténtelo de nuevo.";
  } finally {
    isSaving.value = false;
  }
}

// --- Lógica de Paginación ---
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
  margin: 2rem auto;
  font-family: sans-serif;
}

.pdf-wrapper {
  position: relative; /* CLAVE: Permite que los overlays se posicionen relativos a este contenedor. */
  border: 1px solid #e0e0e0;
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.overlay-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* TRUCO: Permite hacer clic "a través" del contenedor, excepto en sus hijos. */
}

.text-region-overlay {
  position: absolute;
  border: 2px dashed rgba(239, 68, 68, 0.7); /* Rojo para visibilidad */
  background-color: rgba(239, 68, 68, 0.1);
  cursor: pointer;
  pointer-events: auto; /* IMPORTANTE: Habilita los clics solo en los overlays. */
  transition: background-color 0.2s ease-in-out;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.text-region-overlay:hover {
  background-color: rgba(239, 68, 68, 0.3);
}

.edit-icon {
  font-size: 1.5rem;
  opacity: 0;
  color: white;
  text-shadow: 0 0 3px black;
  transition: opacity 0.2s ease-in-out;
}

.text-region-overlay:hover .edit-icon {
  opacity: 1;
}

.controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #f7f7f7;
  border: 1px solid #e0e0e0;
  border-top: none;
  margin-bottom: 2rem;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
}

.pagination button, .save-all-button {
  padding: 0.5em 1em;
  border: 1px solid #ccc;
  background-color: white;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.save-all-button {
  background-color: #28a745;
  color: white;
  border-color: #28a745;
  font-weight: bold;
}

.save-all-button:disabled {
  background-color: #aaa;
  border-color: #aaa;
}

/* --- Estilos del Modal de Edición --- */
.modal-backdrop {
  position: fixed;
  z-index: 1000;
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
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}

.modal-content h3, .modal-content h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.text-comparison {
  background-color: #f8f9fa;
  border-left: 4px solid #dee2e6;
  padding: 0.5rem 1rem;
  margin-bottom: 1.5rem;
  font-size: 0.9em;
}

.text-comparison p {
  margin: 0;
  color: #495057;
  max-height: 100px;
  overflow-y: auto;
}

.modal-content textarea {
  width: 100%;
  box-sizing: border-box;
  font-size: 1rem;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
}

.modal-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.modal-actions button {
    padding: 0.6em 1.2em;
    border-radius: 4px;
    border: none;
    font-weight: bold;
    cursor: pointer;
}
.btn-save {
    background-color: #007bff;
    color: white;
}
.btn-cancel {
    background-color: #6c757d;
    color: white;
}

/* --- Estilos de Carga y Error --- */
.loading-overlay {
  text-align: center;
  padding: 2rem;
}
.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
}
</style>