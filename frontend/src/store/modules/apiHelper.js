export const extractDistinctValues = (objects, property) => {
  const propertyValues = objects.map((object) => object[property]);
  const distinctPropertyValues = [...new Set(propertyValues)];
  return distinctPropertyValues.map((value) => ({ [property]: value }));
};

export async function loadFromApi(
  apiMethod,
  mutationMethod,
  commit,
  processData = null
) {
  try {
    const response = await apiMethod();
    let data = response.data.data;
    if (processData) {
      data = processData(data);
    }
    commit(mutationMethod, data);
  } catch (error) {
    console.error(`Failed to load data using ${apiMethod.name}: `, error);
  }
}
