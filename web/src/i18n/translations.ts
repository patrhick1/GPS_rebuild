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

  // MyImpact wizard chrome
  'Back to Dashboard': 'Volver al tablero',
  'Question': 'Pregunta',
  'Complete': 'Completado',
  '1 = Not true of me': '1 = No es cierto para mí',
  '10 = Consistently true of me': '10 = Es siempre cierto para mí',
  'Loading MyImpact Assessment...': 'Cargando la evaluación MiImpacto...',
  'Fruit of the Spirit': 'Fruto del Espíritu',
  'Your Unique Design': 'Tu diseño único',
  'But the Holy Spirit produces this kind of fruit in our lives: love, joy, peace, patience, kindness, goodness, faithfulness, gentleness, and self-control. Galatians 5:22-23':
    'En cambio, el fruto del Espíritu es amor, alegría, paz, paciencia, amabilidad, bondad, fidelidad, humildad y dominio propio. Gálatas 5:22-23',
  "We are God's handiwork, created in Christ Jesus to do good works, which God prepared in advance for us to do. Ephesians 2:10":
    'Porque somos hechura de Dios, creados en Cristo Jesús para buenas obras, las cuales Dios dispuso de antemano a fin de que las pongamos en práctica. Efesios 2:10',

  // MyImpact results — chrome
  'Your MyImpact Score': 'Tu puntaje MiImpacto',
  'Character × Calling = MyImpact Score': 'Carácter × Llamado = Puntaje MiImpacto',
  'MyImpact': 'MiImpacto',
  'Most first-time takers score between 4-25. The goal is steady growth, not perfection.':
    'La mayoría de quienes la toman por primera vez obtienen entre 4 y 25 puntos. El objetivo es el crecimiento constante, no la perfección.',
  'Average': 'Promedio',
  'Fruit of the Spirit — Rate yourself as those who know you best would rate you.':
    'Fruto del Espíritu — Evalúate como te evaluarían quienes mejor te conocen.',
  'Your Unique Design — Your Calling is the unique way God has designed you to partner with Him.':
    'Tu diseño único — Tu llamado es la forma única en la que Dios te ha diseñado para colaborar con Él.',
  'Growth Opportunities': 'Oportunidades de crecimiento',
  'The goal is steady growth, not perfection. Consider focusing on your lowest-scoring areas to increase your overall impact.':
    'El objetivo es el crecimiento constante, no la perfección. Considera enfocarte en tus áreas con menor puntaje para aumentar tu impacto general.',
  'Retake Regularly': 'Vuelve a tomarla con regularidad',
  'Take this assessment every 6-12 months to track your growth over time.':
    'Toma esta evaluación cada 6 a 12 meses para seguir tu crecimiento a lo largo del tiempo.',
  'Get Feedback': 'Pide retroalimentación',
  'Ask those closest to you how they would rate your character and calling.':
    'Pregunta a tus personas más cercanas cómo evaluarían tu carácter y tu llamado.',
  'Set Goals': 'Fija metas',
  'Focus on 1-2 dimensions at a time for sustainable growth.':
    'Enfócate en 1 o 2 dimensiones a la vez para un crecimiento sostenible.',
  'Generating...': 'Generando...',

  // MyImpact character dimensions (Fruit of the Spirit — Gálatas 5:22-23 NVI)
  'Loving': 'Amoroso',
  'Joyful': 'Alegre',
  'Peaceful': 'Pacífico',
  'Patient': 'Paciente',
  'Kind': 'Amable',
  'Good': 'Bondadoso',
  'Faithful': 'Fiel',
  'Gentle': 'Manso',
  'Self-Controlled': 'Con dominio propio',

  // MyImpact calling dimensions
  'I can name my top 3 Spiritual Gifts': 'Puedo nombrar mis 3 dones espirituales principales',
  'I know the people/causes God wants me to serve': 'Sé a qué personas y causas Dios quiere que sirva',
  'I am using my gifts to serve others': 'Estoy usando mis dones para servir a otros',
  'I see God making a difference through me': 'Veo a Dios marcando la diferencia a través de mí',
  'I experience joy in serving others': 'Experimento alegría al servir a los demás',
  'I regularly pray for people around me': 'Oro regularmente por las personas que me rodean',
  'I see people move toward faith': 'Veo a personas avanzar hacia la fe',
  'I receive support in my calling': 'Recibo apoyo en mi llamado',
};

const translations: Record<Locale, Record<string, string>> = {
  en: {}, // Empty — English is the source-of-truth, returned as-is.
  es,
};

export default translations;
