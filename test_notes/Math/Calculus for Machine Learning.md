# Calculus for Machine Learning

## Derivatives and Gradients

### Single-Variable Derivatives
The derivative measures instantaneous rate of change. For a function f(x), the derivative f'(x) gives the slope at any point.

### Partial Derivatives
For functions of multiple variables, partial derivatives measure change along each dimension while holding others constant.

### Gradient Vectors
The gradient is a vector of partial derivatives, pointing in the direction of steepest increase. It's fundamental to optimization.

## Optimization

### Gradient Descent
Iteratively move in the direction of negative gradient to find local minima. Update rule: `x_new = x_old - learning_rate * gradient`

### Chain Rule
The chain rule enables backpropagation in neural networks, computing gradients through composite functions layer by layer.

### Second-Order Methods
Hessian matrices (second derivatives) provide curvature information, used in advanced optimizers like Newton's method.

## Integration Concepts

### Probability and Expected Value
Integration computes probabilities over continuous distributions and calculates expected values for random variables.

### Loss Functions
The total error across a dataset is often expressed as an integral or sum. Minimizing this guides model training.

## Practical Applications
Calculus underlies all gradient-based learning algorithms. Understanding derivatives helps debug vanishing/exploding gradients and design better architectures.
