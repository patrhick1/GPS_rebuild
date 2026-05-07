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
