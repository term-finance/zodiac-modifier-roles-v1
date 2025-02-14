import { ethers } from "ethers"
import { ParamNativeType } from "../../../../typings/role"
import { makeStyles, TextField } from "@material-ui/core"
import { useEffect, useRef, useState } from "react"
import { formatParamValue, getNativeType } from "../../../../utils/conditions"
import classNames from "classnames"
import { Column } from "../../../commons/layout/Column"

interface ParamConditionInputValueProps {
  param: ethers.utils.ParamType | null
  value: string[]
  disabled?: boolean
  onDecodingError(err: Error): void

  onChange(value: string[]): void
}

const useStyles = makeStyles((theme) => ({
  root: {
    width: "auto !important",
    marginLeft: theme.spacing(1),
    flexGrow: 1,
  },
  error: {
    borderColor: "rgba(255, 0, 0, 0.7)",
  },
  input: {
    padding: theme.spacing(0.5),
    fontSize: 12,
  },
}))

const PlaceholderPerType: Record<ParamNativeType, string> = {
  [ParamNativeType.ARRAY]: "[element 0, value 1, ...]",
  [ParamNativeType.TUPLE]: "[field 0, field 1, ...]",
  [ParamNativeType.BOOLEAN]: "true",
  [ParamNativeType.INT]: "-235000000",
  [ParamNativeType.UINT]: "235000000",
  [ParamNativeType.ADDRESS]: "0xABF...123",
  [ParamNativeType.STRING]: "Enter a string",
  [ParamNativeType.BYTES]: "0x...",
  [ParamNativeType.BYTES_FIXED]: "0x...",
  [ParamNativeType.UNSUPPORTED]: "0x...",
}

function getPlaceholderForType(param: ethers.utils.ParamType | null) {
  const nativeType = getNativeType(param)
  return PlaceholderPerType[nativeType]
}

export const ParamConditionInputValue = ({
  onDecodingError,
  param,
  disabled,
  onChange,
  value,
}: ParamConditionInputValueProps) => {
  const classes = useStyles()

  const valueDecoded = useDecodedValue(param, value[0] || "", onDecodingError)
  const [internalValue, setInternalValue] = useState(valueDecoded)

  useEffect(() => {
    setInternalValue(valueDecoded)
  }, [valueDecoded])

  let valid = !param || tryAbiEncode(param, internalValue) !== null

  const handleChange = (inputValue: string) => {
    setInternalValue(inputValue)
    onChange([tryAbiEncode(param, inputValue) || ""])
  }

  return (
    <TextField
      error={!valid}
      disabled={disabled}
      className={classes.root}
      InputProps={{
        disableUnderline: true,
        className: classNames(classes.input, { [classes.error]: !valid && internalValue.length > 0 }),
      }}
      value={internalValue}
      placeholder={getPlaceholderForType(param)}
      onChange={(evt) => handleChange(evt.target.value)}
    />
  )
}

export const OneOfParamConditionInputValue = ({
  onDecodingError,
  param,
  value,
  disabled,
  onChange,
}: ParamConditionInputValueProps) => {
  const [internalValue, setInternalValue] = useState(value)

  return (
    <Column flexGrow={1}>
      {[
        ...value, //.filter((v) => v.length > 0),
        {}, // add empty element to the end
      ].map((value, index) => (
        <ParamConditionInputValue
          onDecodingError={onDecodingError}
          param={param}
          key={index}
          value={[internalValue[index]]}
          disabled={disabled}
          onChange={(newItemValue: string[]) => {
            const newValue = [...internalValue]
            newValue[index] = newItemValue[0]
            setInternalValue(newValue)
            onChange(newValue.filter((v) => v.length > 0))
          }}
        />
      ))}
    </Column>
  )
}

const useDecodedValue = (
  param: ethers.utils.ParamType | null,
  value: string,
  onDecodingError: (err: Error) => void,
) => {
  const callbackRef = useRef(onDecodingError)
  callbackRef.current = onDecodingError
  const valueDecoded = param ? tryAbiDecode(param, value) : value

  useEffect(() => {
    if (param) {
      tryAbiDecode(param, value, callbackRef.current)
    }
  }, [param, value])

  return valueDecoded
}

const tryAbiEncode = (param: ethers.utils.ParamType | null, value: string) => {
  if (!param) return value

  try {
    return ethers.utils.defaultAbiCoder.encode([param], [formatParamValue(param, value)])
  } catch (err) {
    return null
  }
}

const tryAbiDecode = (param: ethers.utils.ParamType, value: string, onDecodingError?: (err: Error) => void) => {
  if (!value) return value

  const paramTypeString = param.format("full")
  const nativeType = getNativeType(param)
  try {
    const decoded = ethers.utils.defaultAbiCoder.decode([paramTypeString], value)[0]
    return nativeType === ParamNativeType.ARRAY || nativeType === ParamNativeType.TUPLE
      ? JSON.stringify(decoded)
      : decoded.toString()
  } catch (err) {
    console.error("Error decoding value", err, { param, value })
    if (onDecodingError) onDecodingError(err as Error)
    return value
  }
}
