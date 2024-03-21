import { useApiStore } from '../api'
import { useNotificationStore } from '../notification'

const apiStore = useApiStore()
const notificationStore = useNotificationStore()

// Utils
export const extractDistinctValues = (objects, property) => {
  const propertyValues = objects.map((object) => object[property])
  const distinctPropertyValues = [...new Set(propertyValues)]
  return distinctPropertyValues.map((value) => ({ [property]: value }))
}

export function generateCopyName(originalName) {
  const cleanedName = originalName.replace(/\s+/g, ' ').trim()

  const namePattern = cleanedName.match(/(.*\sCopy)(?:\((\d+)\))?$/)
  if (namePattern) {
    const baseName = namePattern[1]
    const copyNum = namePattern[2]
    if (copyNum) {
      return `${baseName}(${parseInt(copyNum) + 1})`
    } else {
      return `${baseName}(1)`
    }
  } else {
    return `${cleanedName} Copy`
  }
}

export function snakeToCamel(snakeCaseStr) {
  return snakeCaseStr.replace(/(_\w)/g, (match) => {
    return match[1].toUpperCase()
  })
}

// API handlers
export async function handleApiRequest({
  httpMethod,
  requestData,
  successNotificationType = 'submitted',
  successMessage = null, // empty for progress notification
  errorMessage = 'An error occurred while processing your request.',
  progressNotificationPayload = null // parameter for progress notification
}) {
  try {
    const response = await apiStore.http[httpMethod](requestData)
    if (response.status === 200 || response.status === 201) {
      if (progressNotificationPayload) {
        notificationStore
          .showProgressNotification(progressNotificationPayload)
      } else {
        notificationStore
          .showGeneralNotification({
            notification: successNotificationType,
            message: successMessage
          })
      }
    }
    return response
  } catch (error) {
    // TODO_error_handling
    console.error(`Failed to process ${httpMethod}.`, error)
    const userErrorMessage = `${errorMessage}. ${error}`
    notificationStore
      .showGeneralNotification({
        notification: 'error',
        message: userErrorMessage
      })
  }
}

export async function getApiData({httpMethod, requestData = {} }) {
  try {
    const response = await apiStore.http[httpMethod](requestData)
    if (response.status === 200) {
      const { data } = response
      return data
    }
  } catch (error) {
    console.error(`Failed to process ${httpMethod}.`, error)
    notificationStore.showGeneralNotification({
      notification: 'error',
      message: error
    })
  }
}
