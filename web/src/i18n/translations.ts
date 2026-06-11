/**
 * Centralized English → Spanish translation table.
 *
 * Pattern: English text is the key, Spanish translation is the value. Pages
 * call `t('English text')` and get the Spanish value when locale='es', the
 * original English when locale='en' or the key is missing.
 *
 * Sources for the Spanish entries:
 *   - Inline ES_STRINGS / ES_RESULTS in AssessmentWizard.tsx and
 *     AssessmentResults.tsx (consolidated here)
 *   - Legacy Laravel translation files in /es/*.php — see in particular
 *     dashboard.php, forms.php, toasts.php, auth.php, assessment.php
 *
 * Why no react-i18next: ~80 strings, no plurals, no formatting needs.
 * The hook is 15 lines. Any future complexity (pluralization, ICU) is the
 * trigger to swap in a real library.
 */

export type Locale = 'en' | 'es';

const es: Record<string, string> = {
  // Assessment wizard (GPS + MyImpact)
  'GPS Assessment': 'Evaluación GPS',
  'MyImpact Assessment': 'Evaluación MiImpacto',
  'Assessment started on': 'Evaluación iniciada el',
  'Completed': 'Completadas',
  'of': 'de',
  'questions': 'preguntas',
  'Statements': 'Declaraciones',
  'Answers': 'Respuestas',
  'Almost Never': 'Casi Nunca',
  'Almost Always': 'Casi Siempre',
  'Previous': 'Anterior',
  'Next': 'Siguiente',
  'Submit': 'Enviar',
  'Submitting...': 'Enviando...',
  'Save & Exit': 'Guardar y Salir',
  'Loading assessment...': 'Cargando evaluación...',
  'No questions available': 'No hay preguntas disponibles',
  'Enter your answer...': 'Ingrese su respuesta...',
  'Assessment menu': 'Menú de evaluación',

  // Assessment results
  'Story': 'Historia',
  'Your Spiritual Gifts': 'Tus Dones Espirituales',
  'Score:': 'Puntaje:',
  'Passions': 'Pasiones',
  'Your Spiritual Influencing Styles (highest score is primary & lower is secondary)':
    'Tus estilos de influencia espiritual (el puntaje más alto es el principal y el más bajo es el secundario)',
  'Your Selections': 'Tus Selecciones',
  'Key Abilities': 'Habilidades Clave',
  "People You're Passionate About": 'Personas que te apasionan',
  'Causes You Care About': 'Causas que te importan',
  'Back': 'Volver',
  'Go Back': 'Volver',
  'Download PDF': 'Descargar PDF',
  'Generating…': 'Generando…',
  'Print': 'Imprimir',
  'Loading results...': 'Cargando resultados...',

  // Dashboard greeting + actions
  'Welcome to Your Dashboard,': 'Bienvenido a su tablero,',
  'Welcome {firstName}! Below are the results of your GPS and MyImpact assessments with their current level of completion. Click to continue with or to review the results of that particular assessment. You can take as many assessments as you wish.':
    '¡Bienvenido {firstName}! A continuación se encuentran los resultados de sus evaluaciones de GPS y MiImpacto con su nivel actual de finalización. Haga clic para continuar o para revisar los resultados de esa evaluación en particular. Puede realizar tantas evaluaciones como desee.',
  'Take New GPS Assessment': 'Tomar una nueva evaluación GPS',
  'Take New MyImpact Assessment': 'Tomar una nueva evaluación MiImpacto',
  'Export My Data': 'Exportar mis datos',
  'Exporting...': 'Exportando...',
  'Loading dashboard...': 'Cargando tablero...',
  'Export downloaded successfully.': 'Exportación descargada con éxito.',
  'Failed to export data. Please try again.': 'No se pudo exportar los datos. Por favor inténtelo de nuevo.',
  'Your request to join {orgName} is awaiting approval.':
    'Su solicitud para unirse a {orgName} está esperando aprobación.',
  'Link My Assessment Results to a Church': 'Vincule los resultados de mi evaluación a una iglesia',
  'Search for your church, submit a request, and get connected once approved.':
    'Busque su iglesia, envíe una solicitud y conéctese una vez aprobada.',
  'Find My Church': 'Buscar mi iglesia',
  'Go to Admin Dashboard': 'Ir al tablero de administrador',
  "Want to access toolkit resources and manage your church's assessment results?":
    '¿Quiere acceder a los recursos del kit de herramientas y gestionar los resultados de la evaluación de su iglesia?',
  'Get the Calling Development Toolkit, which includes Church Admin access to the Disciples Made Impact Dashboard.':
    'Obtenga el Kit de Desarrollo del Llamado, que incluye acceso de administrador de iglesia al Disciples Made Impact Dashboard.',
  'Get Toolkit Access': 'Obtener acceso al kit de herramientas',

  // Dashboard sections + tables
  'GPS Assessments': 'Evaluaciones GPS',
  'MyImpact Assessments': 'Evaluaciones MiImpacto',
  'No GPS assessments yet. Take your first one!': 'Aún no tiene evaluaciones GPS. ¡Tome la primera!',
  'No MyImpact assessments yet. Take your first one!':
    'Aún no tiene evaluaciones MiImpacto. ¡Tome la primera!',
  'Start GPS Assessment': 'Comenzar evaluación GPS',
  'Start MyImpact Assessment': 'Comenzar evaluación MiImpacto',
  'Started': 'Iniciada',
  'Progress': 'Progreso',
  'Gifts': 'Regalos',
  'Passion': 'Pasión',
  'incomplete': 'incompleta',
  'INCOMPLETE': 'INCOMPLETA',
  'View Results': 'Ver resultados',
  'Continue': 'Continuar',
  'MyImpact Score': 'Puntaje MiImpacto',
  'Character': 'Carácter',
  'Calling': 'Llamado',

  // Navigation menu (Dashboard hamburger)
  'Account': 'Cuenta',
  'Update Password': 'Actualizar contraseña',
  'Logout': 'Cerrar sesión',

  // Language toggle (Footer)
  'In English?': 'In English?',
  '¿En español?': '¿En español?',
};

const translations: Record<Locale, Record<string, string>> = {
  en: {}, // Empty — English is the source-of-truth, returned as-is.
  es,
};

export default translations;
