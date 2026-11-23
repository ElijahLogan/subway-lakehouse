output "poller_function_arn" {
  description = "ARN of the poller Lambda function"
  value       = aws_lambda_function.poller.arn
}