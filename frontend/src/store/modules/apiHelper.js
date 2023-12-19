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

export async function handleApiRequest({
  dispatch,
  rootState,
  httpMethod,
  requestData,
  successNotificationType = "submitted",
  successMessage = null, // empty for progress notification
  errorMessage = "An error occurred while processing your request.",
  progressNotificationPayload = null, // parameter for progress notification
}) {
  try {
    const response = await rootState.api.httpClient[httpMethod](requestData);
    if (response.status === 200) {
      if (progressNotificationPayload) {
        dispatch(
          "notification/showProgressNotification",
          progressNotificationPayload,
          { root: true }
        );
      } else {
        dispatch(
          "notification/showGeneralNotification",
          {
            notification: successNotificationType,
            message: successMessage,
          },
          { root: true }
        );
      }
    }
    return response;
  } catch (error) {
    console.error(`Failed to process ${httpMethod}.`, error);
    dispatch(
      "notification/showGeneralNotification",
      {
        notification: "error",
        message: errorMessage,
      },
      { root: true }
    );
  }
}

export function generateCopyName(originalName) {
  const cleanedName = originalName.replace(/\s+/g, " ").trim();

  const namePattern = cleanedName.match(/(.*\sCopy)(?:\((\d+)\))?$/);
  if (namePattern) {
    const baseName = namePattern[1];
    const copyNum = namePattern[2];
    if (copyNum) {
      return `${baseName}(${parseInt(copyNum) + 1})`;
    } else {
      return `${baseName}(1)`;
    }
  } else {
    return `${cleanedName} Copy`;
  }
}

export function snakeToCamel(snakeCaseStr) {
  return snakeCaseStr.replace(/(_\w)/g, (match) => {
    return match[1].toUpperCase();
  });
}
