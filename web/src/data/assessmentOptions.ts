// GPS Assessment Selection Options
// Organized in 3-column layout for MultiSelectPage component

// People Options - Select top 2 (plus 2 custom)
export const PEOPLE_OPTIONS = [
  ['Infants/Babies', 'Toddlers', 'Preschool Children', 'Elementary Children', 'Jr. High Students'],
  ['High School', 'College/Career', 'Women', 'Men', 'Singles'],
  ['Single Parents', 'Young Marrieds', 'Couples', 'Families', 'Older Adults 60+'],
];

// Causes Options - Select top 2 (plus 2 custom)
export const CAUSES_OPTIONS = [
  ['Families/Marriage', 'At-Risk Children', 'Abuse/Violence', 'Financial Management', 'Divorce Recovery'],
  ['Disabilities and/or Support', 'Law and/or Justice System', 'Sanctity of Life', 'Homelessness', 'Recovery'],
  ['Working with prison inmates/families', 'Illness and/or Injury', 'Sexuality and/or Gender Issues', 'Education', 'Policy and/or Politics'],
  ['Race', 'Business and the Economy', 'Relief Efforts', 'Ethics', 'Health and/or Fitness'],
  // Note: 'Regional/State/Federal Issues' was originally 'Regional, State or
  // Federal Issues' — the embedded comma broke the comma-joined storage
  // format used for `multiple_choice_answer`. Renamed 2026-05-07 to use
  // slashes, matching siblings like 'Disabilities and/or Support'.
  ['Science and/or Technology', 'Environment', 'International and Global Affairs', 'Regional/State/Federal Issues', 'Community/Neighborhood Issues'],
];

// Abilities Options - Select top 3 (plus 2 custom)
export const ABILITIES_OPTIONS = [
  ['Project Management', 'Marketing', 'Web Development', 'Music: Vocal', 'Writing', 'Coaching', 'Plumbing', 'Electrical'],
  ['Information Technology', 'Community Relations', 'Graphic Arts', 'Music: Instrumental', 'Training', 'Financial Management', 'Cooking', 'Landscaping/Gardening'],
  ['Communications', 'Social Media', 'Creative Arts', 'Audio Visual', 'Counseling', 'Sports Mechanical', 'Carpentry/Construction'],
];

// Spanish DISPLAY labels for People/Causes/Abilities options.
//
// English keys above remain the canonical stored value in `multiple_choice_answer`
// regardless of locale — that keeps existing data, admin views, and the scoring
// service working without a schema change. The map below is consulted ONLY for
// display, so a Spanish user sees Spanish in the wizard and on results while
// the DB row still says "Young Marrieds".
//
// One translation per English key works across People/Causes/Abilities because
// the few collisions (e.g. "Financial Management" appears in both Causes and
// Abilities) share the same Spanish.
export const OPTION_LABEL_ES: Record<string, string> = {
  // People
  'Infants/Babies': 'Bebés/Infantes',
  'Toddlers': 'Niños pequeños',
  'Preschool Children': 'Niños en edad preescolar',
  'Elementary Children': 'Niños de primaria',
  'Jr. High Students': 'Estudiantes de secundaria',
  'High School': 'Estudiantes de preparatoria',
  'College/Career': 'Universitarios/Profesionales',
  'Women': 'Mujeres',
  'Men': 'Hombres',
  'Singles': 'Solteros',
  'Single Parents': 'Padres/madres solteros',
  'Young Marrieds': 'Recién casados',
  'Couples': 'Parejas',
  'Families': 'Familias',
  'Older Adults 60+': 'Adultos mayores (60+)',
  // Causes
  'Families/Marriage': 'Familias/Matrimonio',
  'At-Risk Children': 'Niños en riesgo',
  'Abuse/Violence': 'Abuso/Violencia',
  'Financial Management': 'Manejo financiero',
  'Divorce Recovery': 'Recuperación del divorcio',
  'Disabilities and/or Support': 'Discapacidad y/o apoyo',
  'Law and/or Justice System': 'Sistema legal y/o judicial',
  'Sanctity of Life': 'Santidad de la vida',
  'Homelessness': 'Personas sin hogar',
  'Recovery': 'Recuperación',
  'Working with prison inmates/families': 'Trabajo con personas en prisión y sus familias',
  'Illness and/or Injury': 'Enfermedad y/o lesiones',
  'Sexuality and/or Gender Issues': 'Asuntos de sexualidad y/o género',
  'Education': 'Educación',
  'Policy and/or Politics': 'Política y/o políticas públicas',
  'Race': 'Raza',
  'Business and the Economy': 'Negocios y economía',
  'Relief Efforts': 'Esfuerzos de ayuda humanitaria',
  'Ethics': 'Ética',
  'Health and/or Fitness': 'Salud y/o estado físico',
  'Science and/or Technology': 'Ciencia y/o tecnología',
  'Environment': 'Medio ambiente',
  'International and Global Affairs': 'Asuntos internacionales y globales',
  'Regional/State/Federal Issues': 'Asuntos regionales/estatales/federales',
  'Community/Neighborhood Issues': 'Asuntos comunitarios/vecinales',
  // Abilities
  'Project Management': 'Gestión de proyectos',
  'Marketing': 'Mercadotecnia',
  'Web Development': 'Desarrollo web',
  'Music: Vocal': 'Música: Vocal',
  'Writing': 'Escritura',
  'Coaching': 'Coaching',
  'Plumbing': 'Plomería',
  'Electrical': 'Electricidad',
  'Information Technology': 'Tecnología de la información',
  'Community Relations': 'Relaciones comunitarias',
  'Graphic Arts': 'Artes gráficas',
  'Music: Instrumental': 'Música: Instrumental',
  'Training': 'Capacitación',
  'Cooking': 'Cocina',
  'Landscaping/Gardening': 'Paisajismo/Jardinería',
  'Communications': 'Comunicaciones',
  'Social Media': 'Redes sociales',
  'Creative Arts': 'Artes creativas',
  'Audio Visual': 'Audiovisual',
  'Counseling': 'Consejería',
  'Sports Mechanical': 'Deportes/Mecánica',
  'Carpentry/Construction': 'Carpintería/Construcción',
};

/**
 * Display an option in the active locale. The stored value is always English;
 * `isEs` callers get the Spanish label when one exists, otherwise the English
 * value passes through (covers custom "Other" entries, which the user typed
 * themselves and we render as-is).
 *
 * For "Other: <text>" pills emitted by the scoring service, we Spanish-ify the
 * "Other" prefix but leave the user's free text untouched.
 */
export function optionLabel(value: string, isEs: boolean): string {
  if (!isEs) return value;
  if (value.startsWith('Other: ')) {
    return `Otro: ${value.slice('Other: '.length)}`;
  }
  return OPTION_LABEL_ES[value] || value;
}
